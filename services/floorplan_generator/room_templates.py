"""Room templates and architectural standards for floorplan generation."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class RoomType(Enum):
    """Standard room types with architectural specifications."""
    LIVING_ROOM = "living_room"
    DINING_ROOM = "dining_room"
    KITCHEN = "kitchen"
    MASTER_BEDROOM = "master_bedroom"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    POWDER_ROOM = "powder_room"
    GARAGE = "garage"
    STUDY = "study"
    UTILITY = "utility"
    PANTRY = "pantry"
    STAIRCASE = "staircase"
    HALLWAY = "hallway"
    VESTIBULE = "vestibule"
    OPEN_TO_SKY = "open_to_sky"


@dataclass
class RoomTemplate:
    """Architectural template for a room type."""
    room_type: RoomType
    min_width: float  # feet
    min_depth: float  # feet
    preferred_width: float  # feet
    preferred_depth: float  # feet
    min_area: float  # sq ft
    preferred_area: float  # sq ft
    requires_window: bool = True
    requires_ventilation: bool = True
    adjacency_preferences: List[RoomType] = None
    furniture_layout: Dict[str, List[Tuple[float, float, float]]] = None  # item: [(x, y, rotation)]
    
    def __post_init__(self):
        if self.adjacency_preferences is None:
            self.adjacency_preferences = []
        if self.furniture_layout is None:
            self.furniture_layout = {}


# Standard room templates based on architectural best practices
ROOM_TEMPLATES: Dict[RoomType, RoomTemplate] = {
    RoomType.LIVING_ROOM: RoomTemplate(
        room_type=RoomType.LIVING_ROOM,
        min_width=12.0,
        min_depth=14.0,
        preferred_width=16.0,
        preferred_depth=18.0,
        min_area=168.0,
        preferred_area=288.0,
        requires_window=True,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.DINING_ROOM, RoomType.KITCHEN, RoomType.HALLWAY],
        furniture_layout={
            "sofa": [(2.0, 3.0, 0)],
            "coffee_table": [(4.0, 3.0, 0)],
            "tv_unit": [(8.0, 1.0, 0)],
        }
    ),
    
    RoomType.DINING_ROOM: RoomTemplate(
        room_type=RoomType.DINING_ROOM,
        min_width=10.0,
        min_depth=12.0,
        preferred_width=14.0,
        preferred_depth=16.0,
        min_area=120.0,
        preferred_area=224.0,
        requires_window=True,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.LIVING_ROOM, RoomType.KITCHEN, RoomType.PANTRY],
        furniture_layout={
            "dining_table": [(3.0, 3.0, 0)],
            "chairs": [(2.5, 2.5, 0), (3.5, 2.5, 0), (2.5, 3.5, 0), (3.5, 3.5, 0)],
        }
    ),
    
    RoomType.KITCHEN: RoomTemplate(
        room_type=RoomType.KITCHEN,
        min_width=8.0,
        min_depth=8.0,
        preferred_width=10.0,
        preferred_depth=12.0,
        min_area=64.0,
        preferred_area=120.0,
        requires_window=True,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.DINING_ROOM, RoomType.PANTRY, RoomType.UTILITY],
        furniture_layout={
            "counter_l": [(1.0, 1.0, 0)],
            "counter_r": [(6.0, 1.0, 0)],
            "island": [(3.5, 4.0, 0)],
            "sink": [(2.0, 1.0, 0)],
            "stove": [(5.0, 1.0, 0)],
        }
    ),
    
    RoomType.MASTER_BEDROOM: RoomTemplate(
        room_type=RoomType.MASTER_BEDROOM,
        min_width=12.0,
        min_depth=14.0,
        preferred_width=16.0,
        preferred_depth=18.0,
        min_area=168.0,
        preferred_area=288.0,
        requires_window=True,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.BATHROOM, RoomType.HALLWAY],
        furniture_layout={
            "bed_king": [(3.0, 3.0, 0)],
            "nightstand_l": [(2.0, 3.0, 0)],
            "nightstand_r": [(5.0, 3.0, 0)],
            "wardrobe": [(7.0, 1.0, 0)],
        }
    ),
    
    RoomType.BEDROOM: RoomTemplate(
        room_type=RoomType.BEDROOM,
        min_width=10.0,
        min_depth=12.0,
        preferred_width=12.0,
        preferred_depth=14.0,
        min_area=120.0,
        preferred_area=168.0,
        requires_window=True,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.BATHROOM, RoomType.HALLWAY],
        furniture_layout={
            "bed_queen": [(2.5, 3.0, 0)],
            "nightstand_l": [(1.5, 3.0, 0)],
            "nightstand_r": [(4.5, 3.0, 0)],
            "desk": [(6.0, 1.0, 0)],
        }
    ),
    
    RoomType.BATHROOM: RoomTemplate(
        room_type=RoomType.BATHROOM,
        min_width=5.0,
        min_depth=6.0,
        preferred_width=6.0,
        preferred_depth=8.0,
        min_area=30.0,
        preferred_area=48.0,
        requires_window=True,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.BEDROOM, RoomType.MASTER_BEDROOM, RoomType.HALLWAY],
        furniture_layout={
            "toilet": [(1.0, 1.0, 0)],
            "sink": [(3.0, 1.0, 0)],
            "shower": [(1.0, 4.0, 0)],
        }
    ),
    
    RoomType.POWDER_ROOM: RoomTemplate(
        room_type=RoomType.POWDER_ROOM,
        min_width=4.0,
        min_depth=5.0,
        preferred_width=5.0,
        preferred_depth=6.0,
        min_area=20.0,
        preferred_area=30.0,
        requires_window=False,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.HALLWAY, RoomType.VESTIBULE],
        furniture_layout={
            "toilet": [(1.0, 1.0, 0)],
            "sink": [(2.5, 1.0, 0)],
        }
    ),
    
    RoomType.GARAGE: RoomTemplate(
        room_type=RoomType.GARAGE,
        min_width=20.0,
        min_depth=22.0,
        preferred_width=24.0,
        preferred_depth=24.0,
        min_area=440.0,
        preferred_area=576.0,
        requires_window=False,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.UTILITY, RoomType.HALLWAY],
        furniture_layout={
            "vehicle": [(2.0, 4.0, 0)],
            "storage": [(15.0, 1.0, 0)],
        }
    ),
    
    RoomType.STUDY: RoomTemplate(
        room_type=RoomType.STUDY,
        min_width=10.0,
        min_depth=12.0,
        preferred_width=12.0,
        preferred_depth=14.0,
        min_area=120.0,
        preferred_area=168.0,
        requires_window=True,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.HALLWAY, RoomType.BEDROOM],
        furniture_layout={
            "desk": [(2.0, 2.0, 0)],
            "chair": [(3.0, 2.0, 0)],
            "bookshelf": [(7.0, 1.0, 0)],
        }
    ),
    
    RoomType.UTILITY: RoomTemplate(
        room_type=RoomType.UTILITY,
        min_width=6.0,
        min_depth=8.0,
        preferred_width=8.0,
        preferred_depth=10.0,
        min_area=48.0,
        preferred_area=80.0,
        requires_window=False,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.KITCHEN, RoomType.GARAGE],
        furniture_layout={
            "washer": [(1.0, 1.0, 0)],
            "dryer": [(3.0, 1.0, 0)],
            "utility_sink": [(5.0, 1.0, 0)],
        }
    ),
    
    RoomType.PANTRY: RoomTemplate(
        room_type=RoomType.PANTRY,
        min_width=5.0,
        min_depth=6.0,
        preferred_width=6.0,
        preferred_depth=8.0,
        min_area=30.0,
        preferred_area=48.0,
        requires_window=False,
        requires_ventilation=False,
        adjacency_preferences=[RoomType.KITCHEN, RoomType.DINING_ROOM],
        furniture_layout={
            "shelves": [(1.0, 1.0, 0)],
            "storage": [(3.0, 1.0, 0)],
        }
    ),
    
    RoomType.STAIRCASE: RoomTemplate(
        room_type=RoomType.STAIRCASE,
        min_width=4.0,
        min_depth=8.0,
        preferred_width=5.0,
        preferred_depth=10.0,
        min_area=32.0,
        preferred_area=50.0,
        requires_window=False,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.HALLWAY, RoomType.VESTIBULE],
        furniture_layout={}
    ),
    
    RoomType.HALLWAY: RoomTemplate(
        room_type=RoomType.HALLWAY,
        min_width=4.0,
        min_depth=8.0,
        preferred_width=5.0,
        preferred_depth=15.0,
        min_area=32.0,
        preferred_area=75.0,
        requires_window=False,
        requires_ventilation=False,
        adjacency_preferences=[],
        furniture_layout={}
    ),
    
    RoomType.VESTIBULE: RoomTemplate(
        room_type=RoomType.VESTIBULE,
        min_width=5.0,
        min_depth=6.0,
        preferred_width=6.0,
        preferred_depth=8.0,
        min_area=30.0,
        preferred_area=48.0,
        requires_window=False,
        requires_ventilation=False,
        adjacency_preferences=[RoomType.HALLWAY, RoomType.LIVING_ROOM],
        furniture_layout={
            "coat_rack": [(1.0, 1.0, 0)],
            "shoe_rack": [(3.0, 1.0, 0)],
        }
    ),
    
    RoomType.OPEN_TO_SKY: RoomTemplate(
        room_type=RoomType.OPEN_TO_SKY,
        min_width=10.0,
        min_depth=3.0,
        preferred_width=15.0,
        preferred_depth=3.5,
        min_area=30.0,
        preferred_area=52.5,
        requires_window=False,
        requires_ventilation=True,
        adjacency_preferences=[RoomType.LIVING_ROOM, RoomType.BEDROOM, RoomType.STUDY],
        furniture_layout={}
    ),
}


def get_template(room_type: RoomType) -> Optional[RoomTemplate]:
    """Get room template by type."""
    return ROOM_TEMPLATES.get(room_type)


def get_all_room_types() -> List[RoomType]:
    """Get all available room types."""
    return list(RoomType)
