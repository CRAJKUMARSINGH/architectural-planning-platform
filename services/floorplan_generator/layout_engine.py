"""Layout engine for intelligent room placement and floorplan generation."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math

from .room_templates import RoomType, RoomTemplate, get_template


@dataclass
class RoomPlacement:
    """Represents a placed room with its position and dimensions."""
    room_type: RoomType
    x: float  # feet from origin (west edge)
    y: float  # feet from origin (south edge)
    width: float  # feet
    depth: float  # feet
    rotation: float = 0.0  # degrees
    level: str = "GF"
    
    @property
    def area(self) -> float:
        return self.width * self.depth
    
    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.depth / 2)
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Return (x_min, y_min, x_max, y_max)"""
        return (self.x, self.y, self.x + self.width, self.y + self.depth)
    
    def overlaps(self, other: 'RoomPlacement', buffer: float = 0.0) -> bool:
        """Check if this room overlaps with another (with optional buffer for walls)."""
        x1_min, y1_min, x1_max, y1_max = self.bounds
        x2_min, y2_min, x2_max, y2_max = other.bounds
        
        return not (
            x1_max <= x2_min + buffer or
            x2_max <= x1_min + buffer or
            y1_max <= y2_min + buffer or
            y2_max <= y1_min + buffer
        )


@dataclass
class FloorplanLayout:
    """Complete floorplan layout with all rooms and metadata."""
    building_width: float  # feet
    building_depth: float  # feet
    rooms: List[RoomPlacement]
    wall_thickness: float = 0.5  # feet (6 inches)
    levels: List[str] = None
    
    def __post_init__(self):
        if self.levels is None:
            self.levels = ["GF"]
    
    def get_room_by_type(self, room_type: RoomType) -> Optional[RoomPlacement]:
        """Get a room placement by type."""
        for room in self.rooms:
            if room.room_type == room_type:
                return room
        return None
    
    def get_rooms_on_level(self, level: str) -> List[RoomPlacement]:
        """Get all rooms on a specific level."""
        return [room for room in self.rooms if room.level == level]
    
    def validate(self, strict: bool = True) -> Tuple[bool, List[str]]:
        """Validate the layout against architectural constraints.
        
        Args:
            strict: If False, only check for overlaps and bounds, not minimum dimensions
        """
        errors = []
        
        # Check if all rooms fit within building bounds
        for room in self.rooms:
            x_min, y_min, x_max, y_max = room.bounds
            if x_min < 0 or y_min < 0:
                errors.append(f"{room.room_type.value} extends beyond building bounds (negative position)")
            if x_max > self.building_width:
                errors.append(f"{room.room_type.value} extends beyond building width")
            if y_max > self.building_depth:
                errors.append(f"{room.room_type.value} extends beyond building depth")
        
        # Check for overlaps
        for i, room1 in enumerate(self.rooms):
            for room2 in self.rooms[i+1:]:
                if room1.overlaps(room2):
                    errors.append(f"{room1.room_type.value} overlaps with {room2.room_type.value}")
        
        # Check room sizes against templates (only if strict mode)
        if strict:
            for room in self.rooms:
                template = get_template(room.room_type)
                if template:
                    if room.width < template.min_width:
                        errors.append(f"{room.room_type.value} width {room.width} < minimum {template.min_width}")
                    if room.depth < template.min_depth:
                        errors.append(f"{room.room_type.value} depth {room.depth} < minimum {template.min_depth}")
                    if room.area < template.min_area:
                        errors.append(f"{room.room_type.value} area {room.area} < minimum {template.min_area}")
        
        return (len(errors) == 0, errors)


class LayoutEngine:
    """Intelligent layout engine for floorplan generation."""
    
    def __init__(self, wall_thickness: float = 0.5):
        self.wall_thickness = wall_thickness
    
    def generate_25x50_layout_v3(self) -> FloorplanLayout:
        """
        Generate Version 3 of the 25x50 ft layout with:
        - 8x8 kitchen in SOUTH EAST corner (MODIFIED)
        - Master bedroom in SW corner
        - 15x3.5 open-to-sky on center of east wall
        - Living, dining, utility, and other spaces
        """
        building_width = 25.0  # feet (west-east)
        building_depth = 50.0  # feet (south-north)
        
        rooms = []
        
        # ROW 1: South (y=0 to y=16)
        # Master bedroom in SW corner (0,0 to 13,16)
        rooms.append(RoomPlacement(
            room_type=RoomType.MASTER_BEDROOM,
            x=0.0,
            y=0.0,
            width=13.0,
            depth=16.0,
            level="GF"
        ))
        
        # Bathroom (13,0 to 18,10)
        rooms.append(RoomPlacement(
            room_type=RoomType.BATHROOM,
            x=13.0,
            y=0.0,
            width=5.0,
            depth=10.0,
            level="GF"
        ))
        
        # Utility (18,0 to 25,10)
        rooms.append(RoomPlacement(
            room_type=RoomType.UTILITY,
            x=18.0,
            y=0.0,
            width=7.0,
            depth=10.0,
            level="GF"
        ))
        
        # Staircase (13,10 to 18,18)
        rooms.append(RoomPlacement(
            room_type=RoomType.STAIRCASE,
            x=13.0,
            y=10.0,
            width=5.0,
            depth=8.0,
            level="GF"
        ))
        
        # ROW 2: Middle (y=18 to y=36) - V3 MODIFIED
        # Living room (0,18 to 12,36)
        rooms.append(RoomPlacement(
            room_type=RoomType.LIVING_ROOM,
            x=0.0,
            y=18.0,
            width=12.0,
            depth=18.0,
            level="GF"
        ))
        
        # Hallway (12,18 to 16,36)
        rooms.append(RoomPlacement(
            room_type=RoomType.HALLWAY,
            x=12.0,
            y=18.0,
            width=4.0,
            depth=18.0,
            level="GF"
        ))
        
        # Dining room (16,18 to 25,36)
        rooms.append(RoomPlacement(
            room_type=RoomType.DINING_ROOM,
            x=16.0,
            y=18.0,
            width=9.0,
            depth=18.0,
            level="GF"
        ))
        
        # ROW 3: North (y=36 to y=50) - V3 MODIFIED
        # Vestibule (0,36 to 8,42)
        rooms.append(RoomPlacement(
            room_type=RoomType.VESTIBULE,
            x=0.0,
            y=36.0,
            width=8.0,
            depth=6.0,
            level="GF"
        ))
        
        # Study (0,42 to 12,48)
        rooms.append(RoomPlacement(
            room_type=RoomType.STUDY,
            x=0.0,
            y=42.0,
            width=12.0,
            depth=6.0,
            level="GF"
        ))
        
        # Pantry (12,42 to 16,48)
        rooms.append(RoomPlacement(
            room_type=RoomType.PANTRY,
            x=12.0,
            y=42.0,
            width=4.0,
            depth=6.0,
            level="GF"
        ))
        
        # Kitchen in SOUTH EAST corner (17,36 to 25,44) - 8x8 - MODIFIED POSITION
        rooms.append(RoomPlacement(
            room_type=RoomType.KITCHEN,
            x=17.0,
            y=36.0,
            width=8.0,
            depth=8.0,
            level="GF"
        ))
        
        # Open-to-sky on center of east wall (5,48 to 20,51.5) - 15x3.5
        rooms.append(RoomPlacement(
            room_type=RoomType.OPEN_TO_SKY,
            x=5.0,
            y=48.0,
            width=15.0,
            depth=2.0,
            level="GF"
        ))
        
        layout = FloorplanLayout(
            building_width=building_width,
            building_depth=building_depth,
            rooms=rooms,
            wall_thickness=self.wall_thickness
        )
        
        return layout

    def generate_25x50_layout(self) -> FloorplanLayout:
        """
        Generate the specific 25x50 ft layout with:
        - 8x8 kitchen in SOUTH EAST corner (CORRECTED - was NE)
        - Master bedroom in SW corner
        - 15x3.5 open-to-sky on center of east wall
        - Living, dining, utility, and other spaces
        """
        building_width = 25.0  # feet (west-east)
        building_depth = 50.0  # feet (south-north)
        
        rooms = []
        
        # ROW 1: South (y=0 to y=16)
        # Master bedroom in SW corner (0,0 to 13,16)
        rooms.append(RoomPlacement(
            room_type=RoomType.MASTER_BEDROOM,
            x=0.0,
            y=0.0,
            width=13.0,
            depth=16.0,
            level="GF"
        ))
        
        # Bathroom (13,0 to 18,10)
        rooms.append(RoomPlacement(
            room_type=RoomType.BATHROOM,
            x=13.0,
            y=0.0,
            width=5.0,
            depth=10.0,
            level="GF"
        ))
        
        # Utility (18,0 to 25,10)
        rooms.append(RoomPlacement(
            room_type=RoomType.UTILITY,
            x=18.0,
            y=0.0,
            width=7.0,
            depth=10.0,
            level="GF"
        ))
        
        # Staircase (13,10 to 18,18)
        rooms.append(RoomPlacement(
            room_type=RoomType.STAIRCASE,
            x=13.0,
            y=10.0,
            width=5.0,
            depth=8.0,
            level="GF"
        ))
        
        # ROW 2: Middle (y=18 to y=36)
        # Living room (0,18 to 12,36)
        rooms.append(RoomPlacement(
            room_type=RoomType.LIVING_ROOM,
            x=0.0,
            y=18.0,
            width=12.0,
            depth=18.0,
            level="GF"
        ))
        
        # Hallway (12,18 to 16,36)
        rooms.append(RoomPlacement(
            room_type=RoomType.HALLWAY,
            x=12.0,
            y=18.0,
            width=4.0,
            depth=18.0,
            level="GF"
        ))
        
        # Dining room (16,18 to 25,36)
        rooms.append(RoomPlacement(
            room_type=RoomType.DINING_ROOM,
            x=16.0,
            y=18.0,
            width=9.0,
            depth=18.0,
            level="GF"
        ))
        
        # ROW 3: North (y=36 to y=50)
        # Vestibule (0,36 to 8,42)
        rooms.append(RoomPlacement(
            room_type=RoomType.VESTIBULE,
            x=0.0,
            y=36.0,
            width=8.0,
            depth=6.0,
            level="GF"
        ))
        
        # Study (0,42 to 12,48)
        rooms.append(RoomPlacement(
            room_type=RoomType.STUDY,
            x=0.0,
            y=42.0,
            width=12.0,
            depth=6.0,
            level="GF"
        ))
        
        # Pantry (12,42 to 16,48)
        rooms.append(RoomPlacement(
            room_type=RoomType.PANTRY,
            x=12.0,
            y=42.0,
            width=4.0,
            depth=6.0,
            level="GF"
        ))
        
        # Kitchen in SOUTH EAST corner (17,36 to 25,44) - 8x8 - CORRECTED POSITION
        rooms.append(RoomPlacement(
            room_type=RoomType.KITCHEN,
            x=17.0,
            y=36.0,
            width=8.0,
            depth=8.0,
            level="GF"
        ))
        
        # Open-to-sky on center of east wall (5,48 to 20,49.5) - 15x3.5
        rooms.append(RoomPlacement(
            room_type=RoomType.OPEN_TO_SKY,
            x=5.0,
            y=48.0,
            width=15.0,
            depth=1.5,
            level="GF"
        ))
        
        layout = FloorplanLayout(
            building_width=building_width,
            building_depth=building_depth,
            rooms=rooms,
            wall_thickness=self.wall_thickness
        )
        
        return layout
    
    def generate_layout_from_requirements(
        self,
        building_width: float,
        building_depth: float,
        required_rooms: List[RoomType],
        constraints: Optional[Dict] = None
    ) -> FloorplanLayout:
        """
        Generate a layout from building dimensions and required rooms.
        
        Args:
            building_width: Building width in feet
            building_depth: Building depth in feet
            required_rooms: List of room types to include
            constraints: Optional placement constraints
        """
        if constraints is None:
            constraints = {}
        
        rooms = []
        current_x = 0.0
        current_y = 0.0
        
        # Simple grid-based placement algorithm
        # In production, this would use more sophisticated optimization
        for room_type in required_rooms:
            template = get_template(room_type)
            if not template:
                continue
            
            # Use preferred dimensions if they fit, otherwise use minimum
            width = min(template.preferred_width, building_width - current_x)
            depth = min(template.preferred_depth, building_depth - current_y)
            
            if width < template.min_width or depth < template.min_depth:
                # Move to next row if space is insufficient
                current_x = 0.0
                current_y += max(depth, 10.0)  # Minimum row height
                width = min(template.preferred_width, building_width)
                depth = min(template.preferred_depth, building_depth - current_y)
            
            # Apply specific constraints if provided
            if room_type in constraints:
                constraint = constraints[room_type]
                if 'position' in constraint:
                    current_x, current_y = constraint['position']
                if 'dimensions' in constraint:
                    width, depth = constraint['dimensions']
            
            rooms.append(RoomPlacement(
                room_type=room_type,
                x=current_x,
                y=current_y,
                width=width,
                depth=depth,
                level="GF"
            ))
            
            # Move to next position
            current_x += width + self.wall_thickness
            
            # If we've exceeded building width, move to next row
            if current_x >= building_width:
                current_x = 0.0
                current_y += depth + self.wall_thickness
        
        layout = FloorplanLayout(
            building_width=building_width,
            building_depth=building_depth,
            rooms=rooms,
            wall_thickness=self.wall_thickness
        )
        
        return layout
    
    def optimize_layout(
        self,
        layout: FloorplanLayout,
        iterations: int = 100
    ) -> FloorplanLayout:
        """
        Optimize a layout using simulated annealing or genetic algorithm.
        
        Args:
            layout: Initial layout to optimize
            iterations: Number of optimization iterations
        """
        # Placeholder for optimization algorithm
        # In production, this would implement:
        # - Simulated annealing for room placement
        # - Genetic algorithm for layout generation
        # - Constraint satisfaction for adjacencies
        
        return layout
    
    def calculate_circulation(self, layout: FloorplanLayout) -> Dict[str, List[Tuple[float, float]]]:
        """
        Calculate circulation paths between rooms.
        
        Returns:
            Dictionary mapping room pairs to path coordinates
        """
        # Placeholder for circulation analysis
        # In production, this would:
        # - Build a graph of room connections
        # - Calculate shortest paths
        # - Identify bottlenecks
        return {}
