import heapq
from src.graph.graph import Graph
from src.models.zone import Zone, ZoneType
from src.simulation.simulator import ReservationTable


class Pathfinder:
    """
    Finds paths for drones while respecting reservation rules.

    Uses a Dijkstra-based search with reservations to avoid
    conflicts between drones.
    """

    def find_path(
        self,
        graph: Graph,
        start: Zone,
        end: Zone,
        nb_drones: int,
        reservations: ReservationTable,
    ) -> list[tuple[Zone, int]]:
        """
        Find a valid path from the start zone to the end zone.

        The search respects zone capacities, connection capacities,
        restricted zones, and existing reservations.

        Args:
            graph: Graph containing all zones and connections.
            start: Starting zone.
            end: Destination zone.
            nb_drones: Total number of drones in the simulation.
            reservations: Reservation table used to avoid conflicts.

        Returns:
            A list of (zone_obj, turn) pairs describing the path.
            Returns an empty list if no valid path is found.
        """
        heap: list[tuple[int, int, int, Zone, list[tuple[Zone, int]]]] = []
        path: list[tuple[Zone, int]] = []
        counter = 0
        heapq.heappush(heap, (0, 0, counter, start, path))
        max_time = len(graph.zones) * nb_drones * 2
        visited: set[tuple[str, int]] = set()

        while heap:

            current_turn, _, _, current_zone_obj, path = heapq.heappop(heap)
            if current_turn >= max_time:
                continue

            current_zone_name = current_zone_obj.name
            state = (current_zone_name, current_turn)
            if state in visited:
                continue
            new_path = path + [(current_zone_obj, current_turn)]
            if current_zone_obj == end:
                return new_path
            visited.add(state)

            # ---------- WAIT ACTION ----------
            wait_turn = current_turn + 1

            if (
                wait_turn <= max_time
                and reservations.can_enter_zone(current_zone_obj, wait_turn)
            ):
                priority = 0 if (
                    current_zone_obj.zone_type == ZoneType.PRIORITY) else 1
                counter += 1
                heapq.heappush(heap, (wait_turn, priority, counter,
                                      current_zone_obj, new_path))

            # ---------- MOVE ACTIONS ----------

            for neighbor in graph.get_neighbors(current_zone_obj):
                arrival_turn = neighbor.get_movement_cost()
                new_turn = current_turn + arrival_turn
                neighbor_state = (neighbor.name, new_turn)
                if neighbor_state in visited:
                    continue
                connection = graph.get_connection(current_zone_obj, neighbor)
                if connection is None:
                    continue

                if not reservations.can_enter_zone(neighbor, new_turn):
                    continue
                connection_ok = True

                for t in range(current_turn + 1,
                               current_turn + arrival_turn + 1):
                    if not reservations.can_use_connection(
                        current_zone_obj,
                        neighbor,
                        t,
                        connection.max_link_capacity
                    ):
                        connection_ok = False
                        break

                if not connection_ok:
                    continue
                priority = 0 if neighbor.zone_type == ZoneType.PRIORITY else 1

                counter += 1
                heapq.heappush(
                    heap,
                    (new_turn, priority, counter, neighbor, new_path))
        return []
