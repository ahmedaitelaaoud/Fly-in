import re
from typing import Dict
from src.data import Zone, Connection
from src.custom_errors import (
    ConnectionException,
    HubException,
    DronesException
    )


class MapParser:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.drones_count = 0
        self.start_zone_name: str | None = None
        self.end_zone_name: str | None = None
        self.zones: Dict[str, Zone] = {}
        self.connections: list[Connection] = []

        self._handlers = {
            "nb_drones:": self._parse_drones,
            "start_hub:": self._parse_start_hub,
            "end_hub:": self._parse_end_hub,
            "hub:": self._parse_hub,
            "connection:": self._parse_connection,
        }

    def parse(self) -> None:
        """Main parsing loop."""
        with open(self.filepath, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                clean_line = line.split('#')[0].strip()
                if not clean_line:
                    continue
                self._route_line(clean_line, line_num)

        self._validate_map()

    def _validate_map(self) -> None:
        """Ensures the map has all required components to run a simulation."""
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

    def _route_line(self, line: str, line_num: int) -> None:
        try:
            prefix, playload = line.split(maxsplit=1)
        except ValueError:
            raise HubException(
                f"Line {line_num}: Missing data after prefix"
            )
        handler = self._handlers.get(prefix)

        if not handler:
            raise HubException(
                f"Line: {line_num} Unkown prefix prefix."
            )

        handler(playload, line_num)

    def _parse_drones(self, payload: str, line_num: int) -> None:
        if self.drones_count != 0:
            raise DronesException(
                f"Line {line_num}: Drone count already defined."
            )

        try:
            count = int(payload.strip())

            if count <= 0:
                raise DronesException(
                    (
                        f"Line {line_num}: Number of drones must be "
                        "a positive integer."
                    )
                )

            self.drones_count = count

        except ValueError:
            raise DronesException(
                f"Line {line_num}: Number of drones must be a valid integer."
            )

    def _parse_start_hub(self, payload: str, line_num: int) -> None:
        if self.start_zone_name is not None:
            raise HubException(
                f"Line {line_num}: Multiple start_hubs defined."
            )

        self._parse_hub(payload, line_num)

        self.start_zone_name = payload.split()[0]

    def _parse_end_hub(self, payload: str, line_num: int) -> None:
        if self.end_zone_name is not None:
            raise HubException(f"Line {line_num}: Multiple end_hubs defined.")

        self._parse_hub(payload, line_num)
        self.end_zone_name = payload.split()[0]

    def _parse_hub(self, playload: str, line_num: int) -> None:
        metadata: Dict[str, str] = {}

        match = re.search(r'\[(.*?)\]', playload)

        if match:
            meta_content = match.group(1)
            pairs = meta_content.split()

            for pair in pairs:
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    metadata[key] = value

            playload = playload[:match.start()].strip()
        parts = playload.split()
        if len(parts) != 3:
            raise HubException(
                f"Line {line_num}: Invalid hub format. Expected "
                "<name> <x> <y>."
            )

        name, x_str, y_str = parts[0], parts[1], parts[2]

        if name in self.zones:
            raise HubException(
                f"Line {line_num}: Duplicate zone name '{name}'"
            )

        try:
            x = int(x_str)
            y = int(y_str)

        except ValueError:
            raise HubException(
                f"Line {line_num}: Coordinates for '{name}' must be integers."
            )
        zone_type = metadata.get('zone', 'normal')

        allowed_types = {'normal', 'restricted', 'priority', 'blocked'}
        if zone_type not in allowed_types:
            raise HubException(
                f"Line {line_num}: Invalid zone type '{zone_type}'."
            )
        try:
            max_drones = int(metadata.get('max_drones', 1))
            if max_drones <= 0:
                raise HubException(
                    f"Line {line_num}: max_drones must be a positive integer."
                )
        except ValueError:
            raise HubException(
                f"Line {line_num}: max_drones must be a valid integer."
            )

        color = metadata.get('color')

        self.zones[name] = Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones
        )

    def _parse_connection(self, payload: str, line_num: int) -> None:
        """Parses connection lines and validates graph integrity."""
        metadata: Dict[str, str] = {}

        match = re.search(r'\[(.*?)\]', payload)

        if match:
            meta_content = match.group(1)
            pairs = meta_content.split()
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    metadata[key] = value

            payload = payload[:match.start()].strip()

        parts = payload.split('-')
        if len(parts) != 2:
            raise ConnectionException(
                f"Line {line_num}: Invalid connection format. "
                "Expected 'zone1-zone2'."
            )

        zone1, zone2 = parts[0].strip(), parts[1].strip()

        if zone1 not in self.zones:
            raise ConnectionException(
                f"Line {line_num}: Unknown zone '{zone1}'."
            )
        if zone2 not in self.zones:
            raise ConnectionException(
                f"Line {line_num}: Unknown zone '{zone2}'."
            )

        if zone1 == zone2:
            raise ConnectionException(
                f"Line {line_num}: Zone '{zone1}' cannot connect to itself."
            )

        for conn in self.connections:
            if (
                (conn.zone1 == zone1 and conn.zone2 == zone2)
                or (conn.zone1 == zone2 and conn.zone2 == zone1)
            ):
                raise ConnectionException(
                    f"Line {line_num}: Duplicate connection between "
                    f"'{zone1}' and '{zone2}'."
                )

        try:
            max_capacity = int(metadata.get('max_link_capacity', 1))
            if max_capacity <= 0:
                raise ConnectionException(
                    f"Line {line_num}: max_link_capacity must be a positive "
                    "integer."
                )
        except ValueError:
            raise ConnectionException(
                f"Line {line_num}: max_link_capacity must be a valid integer."
            )

        self.connections.append(Connection(
            zone1=zone1,
            zone2=zone2,
            max_link_capacity=max_capacity
        ))
