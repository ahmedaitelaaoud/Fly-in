from dataclasses import dataclass
from typing import Optional


@dataclass
class Zone:
    name: str
    x: int
    y: int
    zone_type: str = "normal"
    color: Optional[str] = None
    max_drones: int = 1  # Default by subject


@dataclass
class Connection:
    zone1: str
    zone2: str
    max_link_capacity: int = 1  # Default by subject
