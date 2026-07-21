import re
from collections import deque

from src.custom_errors import ConnectionException, DronesException, HubException
from src.data import Connection, Zone


class MapParser:
    """
    A strict, semantics-aware parser for the Fly-in drone routing simulation.
    Extracts data, enforces rules, and validates graph integrity on the fly.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.drones_count: int = 0
        self.start_zone_name: str | None = None
        self.end_zone_name: str | None = None

        # Parsed Data Collections
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []

        # Fast-Lookup Trackers for Edge Cases
        self._coords_to_zone: dict[tuple[int, int], str] = {}
        self._seen_connections: set[frozenset[str]] = set()
        self._first_prefix: str | None = None

        # The Dispatcher
        self._handlers = {
            "nb_drones:": self._parse_drones,
            "start_hub:": self._parse_start_hub,
            "end_hub:": self._parse_end_hub,
            "hub:": self._parse_hub,
            "connection:": self._parse_connection,
        }

    def __repr__(self) -> str:
        """Pythonic helper for debugging. Allows you to just print(parser)."""
        return (
            f"<MapParser: {self.drones_count} drones, "
            f"{len(self.zones)} zones, {len(self.connections)} connections>"
        )

    def parse(self) -> None:
        """Main parsing loop. Processes the file line-by-line."""
        with open(self.filepath, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                clean_line = line.split("#")[0].strip()
                if not clean_line:
                    continue

                prefix = clean_line.split(maxsplit=1)[0]

                if self._first_prefix is None:
                    self._first_prefix = prefix
                    if self._first_prefix != "nb_drones:":
                        raise DronesException(
                            f"Line {line_num}: First line must be 'nb_drones:'."
                        )

                self._route_line(clean_line, line_num)

        self._validate_map()


    def _validate_map(self) -> None:
        """Ensures the fully parsed map has all required components."""
        if self.drones_count == 0:
            raise DronesException(
                "Invalid Map: File does not define 'nb_drones'."
            )
        if self.start_zone_name is None:
            raise HubException("Invalid Map: No 'start_hub' defined.")
        if self.end_zone_name is None:
            raise HubException("Invalid Map: No 'end_hub' defined.")
        if not self.connections:
            raise ConnectionException("Invalid Map: No connections defined.")

        start_zone = self.zones[self.start_zone_name]
        end_zone = self.zones[self.end_zone_name]

        if start_zone.zone_type == "blocked" or end_zone.zone_type == "blocked":
            raise HubException(
                "Invalid Map: Start/End hubs cannot be 'blocked'."
            )

        if (start_zone.x, start_zone.y) == (end_zone.x, end_zone.y):
            raise HubException(
                "Invalid Map: 'start_hub' and 'end_hub' cannot share coords."
            )

        self._validate_connectivity()

    def _validate_connectivity(self) -> None:
        """
        Runs a Breadth-First Search (BFS) to prove a valid path exists
        from start to end, strictly ignoring 'blocked' zones.
        """
        adjacency: dict[str, set[str]] = {name: set() for name in self.zones}
        for conn in self.connections:
            adjacency[conn.zone1].add(conn.zone2)
            adjacency[conn.zone2].add(conn.zone1)

        start = self.start_zone_name
        end = self.end_zone_name

        if start is None or end is None:
            return

        if not adjacency[start] or not adjacency[end]:
            raise ConnectionException(
                "Invalid Map: Start and End hubs must have connections."
            )

        visited = {start}
        queue = deque([start])

        while queue:
            current = queue.popleft()
            if current == end:
                return  # Success! A valid path exists.

            for neighbor in adjacency[current]:
                if self.zones[neighbor].zone_type == "blocked":
                    continue

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        raise ConnectionException(
            "Invalid Map: No passable path exists between start and end."
        )


    def _route_line(self, line: str, line_num: int) -> None:
        """Routes a cleaned line to its specific parsing method."""
        try:
            prefix, payload = line.split(maxsplit=1)
        except ValueError:
            raise HubException(
                f"Line {line_num}: Missing data after '{line}'."
            )

        handler = self._handlers.get(prefix)
        if not handler:
            raise HubException(f"Line {line_num}: Unknown prefix '{prefix}'.")

        handler(payload, line_num)

    def _extract_metadata(
        self,
        payload: str,
        line_num: int,
        allowed_keys: set[str],
        error_cls: type[Exception],
    ) -> tuple[str, dict[str, str]]:
        """Safely isolates and extracts metadata blocks with format checking."""
        metadata: dict[str, str] = {}

        if payload.count("[") != payload.count("]"):
            raise error_cls(f"Line {line_num}: Unbalanced metadata brackets.")

        matches = list(re.finditer(r"\[(.*?)\]", payload))
        if len(matches) > 1:
            raise error_cls(f"Line {line_num}: Too many metadata blocks.")

        if not matches:
            return payload.strip(), metadata

        match = matches[0]
        meta_content = match.group(1).strip()
        clean_payload = payload[: match.start()].strip()
        trailing = payload[match.end() :].strip()

        if trailing:
            raise error_cls(
                f"Line {line_num}: Metadata must be at the end of the line."
            )

        if not meta_content:
            return clean_payload, metadata

        for token in meta_content.split():
            if token.count("=") != 1:
                raise error_cls(
                    f"Line {line_num}: Invalid metadata token '{token}'."
                )

            key, value = token.split("=", 1)
            if not key or not value:
                raise error_cls(
                    f"Line {line_num}: Invalid metadata token '{token}'."
                )
            if key in metadata:
                raise error_cls(
                    f"Line {line_num}: Duplicate metadata key '{key}'."
                )
            if key not in allowed_keys:
                raise error_cls(
                    f"Line {line_num}: Unknown metadata key '{key}'."
                )

            metadata[key] = value

        return clean_payload, metadata

    def _parse_drones(self, payload: str, line_num: int) -> None:
        """Parses the drone count requirement."""
        if self.drones_count != 0:
            raise DronesException(
                f"Line {line_num}: Drone count already defined."
            )

        try:
            count = int(payload.strip())
        except ValueError:
            raise DronesException(
                f"Line {line_num}: Drone count must be a valid integer."
            )

        if count <= 0:
            raise DronesException(
                f"Line {line_num}: Drone count must be a positive integer."
            )

        self.drones_count = count

    def _parse_start_hub(self, payload: str, line_num: int) -> None:
        if self.start_zone_name is not None:
            raise HubException(
                f"Line {line_num}: Multiple start_hubs defined."
            )
        self._parse_hub(payload, line_num)
        self.start_zone_name = payload.split()[0]

    def _parse_end_hub(self, payload: str, line_num: int) -> None:
        if self.end_zone_name is not None:
            raise HubException(
                f"Line {line_num}: Multiple end_hubs defined."
            )
        self._parse_hub(payload, line_num)
        self.end_zone_name = payload.split()[0]

    def _parse_hub(self, payload: str, line_num: int) -> None:
        """Parses a hub definition and its metadata."""
        payload, metadata = self._extract_metadata(
            payload,
            line_num,
            allowed_keys={"zone", "color", "max_drones"},
            error_cls=HubException,
        )

        parts = payload.split()
        if len(parts) != 3:
            raise HubException(
                f"Line {line_num}: Invalid hub format. Expected <name> <x> <y>."
            )

        name, x_str, y_str = parts

        if "-" in name:
            raise HubException(
                f"Line {line_num}: Zone name '{name}' cannot contain dashes."
            )

        if name in self.zones:
            raise HubException(
                f"Line {line_num}: Duplicate zone name '{name}'."
            )

        try:
            x, y = int(x_str), int(y_str)
        except ValueError:
            raise HubException(
                f"Line {line_num}: Coordinates for '{name}' must be integers."
            )

        coord = (x, y)
        if coord in self._coords_to_zone:
            existing = self._coords_to_zone[coord]
            raise HubException(
                f"Line {line_num}: Coordinates overlap with zone '{existing}'."
            )

        zone_type = metadata.get("zone", "normal")
        if zone_type not in {"normal", "restricted", "priority", "blocked"}:
            raise HubException(
                f"Line {line_num}: Invalid zone type '{zone_type}'."
            )

        try:
            max_drones = int(metadata.get("max_drones", "1"))
        except ValueError:
            raise HubException(
                f"Line {line_num}: max_drones must be an integer."
            )

        if max_drones <= 0:
            raise HubException(
                f"Line {line_num}: max_drones must be positive."
            )

        self.zones[name] = Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=metadata.get("color"),
            max_drones=max_drones,
        )
        self._coords_to_zone[coord] = name

    def _parse_connection(self, payload: str, line_num: int) -> None:
        """Parses bidirectional edges and checks graph integrity."""
        payload, metadata = self._extract_metadata(
            payload,
            line_num,
            allowed_keys={"max_link_capacity"},
            error_cls=ConnectionException,
        )

        parts = payload.split("-")
        if len(parts) != 2:
            raise ConnectionException(
                f"Line {line_num}: Invalid connection format. Expected A-B."
            )

        zone1, zone2 = parts[0].strip(), parts[1].strip()

        if zone1 not in self.zones or zone2 not in self.zones:
            raise ConnectionException(
                f"Line {line_num}: Unknown zone in connection."
            )

        if zone1 == zone2:
            raise ConnectionException(
                f"Line {line_num}: Zone '{zone1}' cannot connect to itself."
            )

        connection_pair = frozenset([zone1, zone2])
        if connection_pair in self._seen_connections:
            raise ConnectionException(
                f"Line {line_num}: Duplicate connection '{zone1}-{zone2}'."
            )
        self._seen_connections.add(connection_pair)

        try:
            max_capacity = int(metadata.get("max_link_capacity", "1"))
        except ValueError:
            raise ConnectionException(
                f"Line {line_num}: max_link_capacity must be an integer."
            )

        if max_capacity <= 0:
            raise ConnectionException(
                f"Line {line_num}: max_link_capacity must be positive."
            )

        self.connections.append(
            Connection(
                zone1=zone1,
                zone2=zone2,
                max_link_capacity=max_capacity,
            )
        )
