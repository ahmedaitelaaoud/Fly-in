from dataclasses import dataclass

from src.data import Zone
from src.parser import MapParser


@dataclass
class Edge:
    """Represents a navigable path to a neighboring node."""
    target: str  # destination zone name
    capacity: int  # max_link_capacity
    current_traffic: int = 0

    def has_capacity(self) -> bool:
        """Checks if another drone can enter this connection this turn."""
        return self.current_traffic < self.capacity

    def reset(self) -> None:
        """Clears traffic state for a new simulation run."""
        self.current_traffic = 0


class Node:
    """Represents a vertex in the graph, wrapping the static Zone data."""

    def __init__(self, zone_data: Zone) -> None:
        self.zone = zone_data           # The static data from the parser
        self.edges: list[Edge] = []     # The Adjacency List for THIS node

        # Simulation State
        self.current_occupancy: int = 0

    @property
    def name(self) -> str:
        """Convenience property to quickly get the node's name."""
        return self.zone.name

    @property
    def cost(self) -> int:
        """Determines movement cost based on the 42 subject rules."""
        if self.zone.zone_type == "restricted":
            return 2
        return 1  # 'normal' and 'priority' both cost 1 turn

    def add_edge(self, target_name: str, capacity: int) -> None:
        """Adds a new outgoing connection from this node."""
        self.edges.append(Edge(target=target_name, capacity=capacity))

    def can_enter(self) -> bool:
        """Validates if the node can accept another drone this turn."""
        return self.current_occupancy < self.zone.max_drones

    def reset(self) -> None:
        """Clears occupancy state for a new simulation run."""
        self.current_occupancy = 0
        for edge in self.edges:
            edge.reset()


class Graph:
    """
    The master engine of the map. Converts raw parsed data into a
    fully navigable, state-aware Adjacency List.
    """

    def __init__(self, parser: MapParser) -> None:
        self.drones_count = parser.drones_count

        # The core Adjacency List: maps zone names to their active Node objects
        self.nodes: dict[str, Node] = {}

        # 1. Convert all static Zones into active Nodes
        for name, zone_data in parser.zones.items():
            self.nodes[name] = Node(zone_data)

        # 2. Wire up the edges (Crucial: Subject says connections are bidirectional)
        for conn in parser.connections:
            # Add an edge from Zone1 -> Zone2
            self.nodes[conn.zone1].add_edge(conn.zone2, conn.max_link_capacity)

            # Add an edge from Zone2 -> Zone1
            self.nodes[conn.zone2].add_edge(conn.zone1, conn.max_link_capacity)

        # 3. Save direct pointers to the start and end nodes for O(1) access
        # (We can safely ignore mypy/type-checking warnings here because our
        # parser already guaranteed these exist and are not None)
        self.start_node = self.nodes[parser.start_zone_name]  # type: ignore
        self.end_node = self.nodes[parser.end_zone_name]      # type: ignore

    def reset_state(self) -> None:
        """Resets the entire graph state to 0 so the simulation can be restarted."""
        for node in self.nodes.values():
            node.reset()
