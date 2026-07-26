from src.models.connection import Connection
from src.models.zone import Zone, ZoneType


class Graph:
    """
    Represents an undirected graph of zones connected by connections.

    Args:
        zones: Dictionary mapping zone names to Zone objects.
        connections: List of connections between zones.

    Attributes:
        zones: Dictionary mapping zone names to Zone objects.
        connections: List of graph connections.
        adjacency_list: Dictionary mapping zones to their connections.
    """

    def __init__(self, zones: dict[str, Zone],
                 connections: list[Connection]) -> None:
        """
        Initialize a graph with zones and their connections.

        Args:
            zones: Dictionary of zone names and corresponding Zone objects.
            connections: List of connections linking zones together.
        """
        self.zones = zones
        self.connections = connections
        self.adjacency_list: dict[Zone, list[Connection]] = {
            z: [] for z in zones.values()}
        for connection in connections:
            self.adjacency_list[connection.zone_a].append(connection)
            self.adjacency_list[connection.zone_b].append(connection)

    def get_neighbors(self, zone: Zone) -> list[Zone]:
        """
        Return all zones directly connected to the given zone.

        Args:
            zone: The zone whose neighbors are requested.

        Returns:
            A list of neighboring Zone objects.
        """
        neighbors: list[Zone] = []
        for connection in self.adjacency_list.get(zone, []):
            if connection.zone_a == zone:
                if connection.zone_b.zone_type != ZoneType.BLOCKED:
                    neighbors.append(connection.zone_b)
            elif connection.zone_b == zone:
                if connection.zone_a.zone_type != ZoneType.BLOCKED:
                    neighbors.append(connection.zone_a)
        return neighbors

    def get_connection(self, zone_a: Zone, zone_b: Zone) -> Connection | None:
        """
        Find the connection between two zones.

        Since the graph is undirected, the order of the zones
        does not matter.

        Args:
            zone_a: First zone.
            zone_b: Second zone.

        Returns:
            The Connection object linking the two zones, or None
            if no connection exists.
        """
        for conn in self.adjacency_list.get(zone_a, []):
            if (conn.zone_a == zone_a and conn.zone_b == zone_b) or \
               (conn.zone_a == zone_b and conn.zone_b == zone_a):
                return conn
        return None

    def get_object_zone(self, name: str) -> Zone | None:
        """
        Return the zone with the given name.

        Args:
            name: Name of the zone.

        Returns:
            The matching Zone object, or None if it does not exist.
        """
        return self.zones.get(name)
