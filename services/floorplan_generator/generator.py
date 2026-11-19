"""Main floorplan generator service."""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

from .room_templates import RoomType, get_template
from .layout_engine import LayoutEngine, FloorplanLayout, RoomPlacement


@dataclass
class FloorplanRequest:
    """Request for floorplan generation."""
    building_width: float  # feet
    building_depth: float  # feet
    required_rooms: List[str]  # Room type names
    constraints: Optional[Dict[str, Any]] = None
    style: str = "modern"
    include_furniture: bool = True
    include_3d: bool = False
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}


@dataclass
class FloorplanResponse:
    """Response from floorplan generation."""
    success: bool
    layout: Optional[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class FloorplanGenerator:
    """AI-powered floorplan generator."""
    
    def __init__(self, wall_thickness: float = 0.5):
        self.layout_engine = LayoutEngine(wall_thickness=wall_thickness)
    
    def generate(self, request: FloorplanRequest) -> FloorplanResponse:
        """
        Generate a floorplan from the request.
        
        Args:
            request: Floorplan generation request
            
        Returns:
            FloorplanResponse with layout data or errors
        """
        errors = []
        
        try:
            # Convert room type strings to RoomType enum
            room_types = []
            for room_name in request.required_rooms:
                try:
                    room_type = RoomType(room_name)
                    room_types.append(room_type)
                except ValueError:
                    errors.append(f"Unknown room type: {room_name}")
            
            if errors:
                return FloorplanResponse(
                    success=False,
                    layout=None,
                    errors=errors,
                    metadata={}
                )
            
            # Check if this is the specific 25x50 layout
            if (request.building_width == 25.0 and 
                request.building_depth == 50.0 and
                RoomType.KITCHEN in room_types and
                RoomType.MASTER_BEDROOM in room_types):
                # Check for version in constraints
                if request.constraints and request.constraints.get('version') == 'v3':
                    layout = self.layout_engine.generate_25x50_layout_v3()
                else:
                    layout = self.layout_engine.generate_25x50_layout()
            else:
                layout = self.layout_engine.generate_layout_from_requirements(
                    building_width=request.building_width,
                    building_depth=request.building_depth,
                    required_rooms=room_types,
                    constraints=request.constraints
                )
            
            # Validate the layout (non-strict for compact layouts)
            is_valid, validation_errors = layout.validate(strict=False)
            if not is_valid:
                errors.extend(validation_errors)
            
            # Convert to serializable format
            layout_dict = self._layout_to_dict(layout, request.include_furniture)
            
            metadata = {
                "generated_at": datetime.utcnow().isoformat(),
                "building_dimensions": f"{request.building_width}x{request.building_depth} ft",
                "total_rooms": len(layout.rooms),
                "total_area": request.building_width * request.building_depth,
                "style": request.style,
                "validation": "passed" if is_valid else "failed"
            }
            
            return FloorplanResponse(
                success=is_valid,
                layout=layout_dict,
                errors=errors,
                metadata=metadata
            )
            
        except Exception as e:
            errors.append(f"Generation failed: {str(e)}")
            return FloorplanResponse(
                success=False,
                layout=None,
                errors=errors,
                metadata={}
            )
    
    def _layout_to_dict(
        self,
        layout: FloorplanLayout,
        include_furniture: bool = True
    ) -> Dict[str, Any]:
        """Convert layout to dictionary format."""
        rooms_dict = []
        
        for room in layout.rooms:
            room_data = {
                "id": f"room-{room.room_type.value}-{len(rooms_dict)}",
                "type": room.room_type.value,
                "position": {"x": room.x, "y": room.y},
                "dimensions": {"width": room.width, "depth": room.depth},
                "area": room.area,
                "center": {"x": room.center[0], "y": room.center[1]},
                "level": room.level,
                "bounds": {
                    "x_min": room.bounds[0],
                    "y_min": room.bounds[1],
                    "x_max": room.bounds[2],
                    "y_max": room.bounds[3]
                }
            }
            
            # Add template information
            template = get_template(room.room_type)
            if template:
                room_data["template"] = {
                    "min_area": template.min_area,
                    "preferred_area": template.preferred_area,
                    "requires_window": template.requires_window,
                    "requires_ventilation": template.requires_ventilation
                }
            
            # Add furniture if requested
            if include_furniture and template and template.furniture_layout:
                room_data["furniture"] = []
                for item_name, positions in template.furniture_layout.items():
                    for pos in positions:
                        x, y, rotation = pos
                        # Scale furniture position to room dimensions
                        scale_x = room.width / template.preferred_width
                        scale_y = room.depth / template.preferred_depth
                        room_data["furniture"].append({
                            "item": item_name,
                            "position": {
                                "x": room.x + x * scale_x,
                                "y": room.y + y * scale_y
                            },
                            "rotation": rotation
                        })
            
            rooms_dict.append(room_data)
        
        return {
            "building": {
                "width": layout.building_width,
                "depth": layout.building_depth,
                "area": layout.building_width * layout.building_depth,
                "wall_thickness": layout.wall_thickness
            },
            "rooms": rooms_dict,
            "levels": layout.levels
        }
    
    def get_room_templates(self) -> List[Dict[str, Any]]:
        """Get all available room templates."""
        templates = []
        for room_type in RoomType:
            template = get_template(room_type)
            if template:
                templates.append({
                    "type": room_type.value,
                    "min_dimensions": {
                        "width": template.min_width,
                        "depth": template.min_depth
                    },
                    "preferred_dimensions": {
                        "width": template.preferred_width,
                        "depth": template.preferred_depth
                    },
                    "min_area": template.min_area,
                    "preferred_area": template.preferred_area,
                    "requires_window": template.requires_window,
                    "requires_ventilation": template.requires_ventilation
                })
        return templates
    
    def get_preset_layouts(self) -> List[Dict[str, Any]]:
        """Get available preset layouts."""
        return [
            {
                "id": "25x50-residential",
                "name": "25x50 ft Residential",
                "description": "Standard 25x50 ft layout with kitchen, master bedroom, and open-to-sky",
                "dimensions": {"width": 25.0, "depth": 50.0},
                "rooms": [
                    "living_room", "dining_room", "kitchen", "master_bedroom",
                    "bathroom", "garage", "utility", "pantry", "staircase",
                    "hallway", "vestibule", "study", "open_to_sky"
                ]
            },
            {
                "id": "30x40-studio",
                "name": "30x40 ft Studio Apartment",
                "description": "Compact studio layout",
                "dimensions": {"width": 30.0, "depth": 40.0},
                "rooms": ["living_room", "kitchen", "bathroom"]
            },
            {
                "id": "40x60-family",
                "name": "40x60 ft Family Home",
                "description": "Spacious family home layout",
                "dimensions": {"width": 40.0, "depth": 60.0},
                "rooms": [
                    "living_room", "dining_room", "kitchen", "master_bedroom",
                    "bedroom", "bedroom", "bathroom", "bathroom", "garage",
                    "utility", "staircase", "hallway"
                ]
            }
        ]
