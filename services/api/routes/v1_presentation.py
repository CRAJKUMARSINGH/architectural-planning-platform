"""Phase 8 — Presentation API routes for scene compilation and rendering."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.api.auth import AuthUser
from services.api.authorization import require_membership_role, require_project_viewer
from services.api.db.session import get_session
from packages.geometry.presentation import (
    ASSET_CATALOG,
    ASSET_CATALOG_VERSION,
    CAMERA_PRESETS,
    STYLE_TOKENS,
    build_render_manifest,
    compile_presentation_scene,
    render_presentation_svg,
)
from packages.geometry.vector_overlays import (
    add_vector_overlays_to_svg,
    calculate_room_labels,
    calculate_wall_dimensions,
)
from packages.geometry.blender_render import (
    render_with_blender_headless,
    validate_blender_environment,
)

router = APIRouter(prefix="/v1/presentation", tags=["presentation-v1"])


class RenderRequest(BaseModel):
    model_sha256: str = Field(..., description="SHA-256 hash of the canonical model")
    style_version: str = Field(default="presentation-residential-v1", description="Style version to use")
    camera_preset: str = Field(default="top-down-plan", description="Camera preset")
    output_kind: str = Field(default="svg", description="Output format")
    include_dimensions: bool = Field(default=True, description="Include dimension lines")
    include_labels: bool = Field(default=True, description="Include room labels")
    seed: int = Field(default=1516, description="Random seed for deterministic rendering")


class CompileRequest(BaseModel):
    model: dict[str, Any] = Field(..., description="Canonical model data")
    style_version: str = Field(default="presentation-residential-v1")
    camera_preset: str = Field(default="top-down-plan")
    seed: int = Field(default=1516)


@router.get("/assets")
def list_assets(_: Any = require_membership_role("viewer")):
    """List all available presentation assets with clearance envelopes."""
    return {
        "version": ASSET_CATALOG_VERSION,
        "assets": ASSET_CATALOG,
        "count": len(ASSET_CATALOG),
    }


@router.get("/styles")
def list_styles(_: Any = require_membership_role("viewer")):
    """List all available presentation style tokens."""
    return {
        "styles": STYLE_TOKENS,
        "count": len(STYLE_TOKENS),
    }


@router.get("/cameras")
def list_camera_presets(_: Any = require_membership_role("viewer")):
    """List all available camera presets."""
    return {
        "presets": CAMERA_PRESETS,
        "count": len(CAMERA_PRESETS),
    }


@router.post("/compile")
def compile_scene(
    req: CompileRequest,
    _: Any = require_membership_role("editor"),
):
    """Compile canonical model into technical and presentation scene graphs."""
    try:
        compiled = compile_presentation_scene(
            model=req.model,
            style_version=req.style_version,
            camera_preset=req.camera_preset,
            seed=req.seed,
        )
        return compiled
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scene compilation failed: {str(e)}")


@router.post("/render/svg")
def render_svg(
    req: RenderRequest,
    _: Any = require_membership_role("editor"),
):
    """Render presentation as SVG with optional overlays."""
    # In a real implementation, we would load the model from object storage
    # For now, return a mock response with the render manifest
    manifest = build_render_manifest(
        model_sha256=req.model_sha256,
        style_version=req.style_version,
        camera_preset=req.camera_preset,
        output_kind=req.output_kind,
        seed=req.seed,
    )
    
    return {
        "success": True,
        "renderManifest": manifest,
        "message": "SVG rendering endpoint - requires model loading from object storage",
    }


@router.get("/blender/status")
def blender_status(_: Any = require_membership_role("viewer")):
    """Check Blender headless rendering availability."""
    return validate_blender_environment()


@router.post("/render/blender")
def render_with_blender(
    req: RenderRequest,
    _: Any = require_membership_role("editor"),
):
    """Render presentation using Blender headless mode."""
    env_status = validate_blender_environment()
    
    if not env_status.get("blender_available"):
        raise HTTPException(
            status_code=503,
            detail="Blender not available for headless rendering"
        )
    
    # In a real implementation, we would:
    # 1. Load the compiled scene from object storage
    # 2. Generate a temporary output path
    # 3. Call render_with_blender_headless
    # 4. Return the rendered artifact
    
    return {
        "success": True,
        "message": "Blender rendering endpoint - requires compiled scene from object storage",
        "blenderStatus": env_status,
    }