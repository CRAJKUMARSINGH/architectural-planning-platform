"""Floorplan generator API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from services.floorplan_generator import FloorplanGenerator, FloorplanRequest as GenRequest


router = APIRouter(prefix="/floorplan", tags=["floorplan"])


class FloorplanRequest(BaseModel):
    """API request for floorplan generation."""
    building_width: float = Field(..., gt=0, description="Building width in feet")
    building_depth: float = Field(..., gt=0, description="Building depth in feet")
    required_rooms: List[str] = Field(..., description="List of room type names")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Optional placement constraints")
    style: str = Field("modern", description="Architectural style")
    include_furniture: bool = Field(True, description="Include furniture in layout")
    include_3d: bool = Field(False, description="Generate 3D visualization data")


class FloorplanResponse(BaseModel):
    """API response for floorplan generation."""
    success: bool
    layout: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Initialize generator
generator = FloorplanGenerator(wall_thickness=0.5)


@router.post("/generate", response_model=FloorplanResponse)
async def generate_floorplan(request: FloorplanRequest) -> FloorplanResponse:
    """
    Generate a floorplan from building dimensions and room requirements.
    
    Example request:
    ```json
    {
        "building_width": 25.0,
        "building_depth": 50.0,
        "required_rooms": [
            "living_room", "dining_room", "kitchen", "master_bedroom",
            "bathroom", "garage", "utility", "pantry", "staircase",
            "hallway", "vestibule", "study", "open_to_sky"
        ],
        "style": "modern",
        "include_furniture": true
    }
    ```
    """
    try:
        gen_request = GenRequest(
            building_width=request.building_width,
            building_depth=request.building_depth,
            required_rooms=request.required_rooms,
            constraints=request.constraints,
            style=request.style,
            include_furniture=request.include_furniture,
            include_3d=request.include_3d
        )
        
        response = generator.generate(gen_request)
        
        return FloorplanResponse(
            success=response.success,
            layout=response.layout,
            errors=response.errors,
            metadata=response.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_room_templates():
    """Get all available room templates with specifications."""
    return {"templates": generator.get_room_templates()}


@router.get("/presets")
async def get_preset_layouts():
    """Get available preset layouts."""
    return {"presets": generator.get_preset_layouts()}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "floorplan-generator"}
