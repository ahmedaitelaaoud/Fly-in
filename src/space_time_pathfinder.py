import heapq
import itertools
from typing import Optional

from src.graph import Graph


class ReservationTable:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.nodes: dict[tuple[str, int], int] = {}  #  ("room_name", turn_number) : number_of_drones_currently_booked
        self.edges: dict[tuple[frozenset[str], int], int] = {} # (frozenset(room_A, room_B), turn_number) : current_traffic.

    def can_occupy_node(self, node_name: str, turn: int) -> bool:
        max_capacity = self.graph.nodes[node_name].zone.max_drones
        current_occupancy = self.nodes.get((node_name, turn), 0)
        return current_occupancy < max_capacity

    def can_traverse_edge(self, u: str, v: str, capacity: int, turn: int)-> bool:
        edge_key = frozenset([u, v])
        current_traffic = self.edges.get((edge_key, turn), 0)
        return current_traffic < capacity

    def reserve_path(self, path: list[tuple[str, int]]) -> None:
        for i in range(len(path)):
            curr_name, curr_turn = path[i]
            self.nodes[(curr_name, curr_turn)] = self.nodes.get((curr_name, curr_turn), 0) + 1  # Reserve
            # Reserve the connection
            if i < len(path) - 1:
                next_name, next_turn = path[i + 1]
                if curr_name != next_name:
                    edge_key = frozenset([curr_name, next_name])
                    for t in range(curr_turn, next_turn):
                        self.edges[(edge_key, t)] = self.edges.get((edge_key, t), 0) + 1


class PathFinder:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.reservations = ReservationTable(graph)
        self.max_turn_limit = len(graph.nodes) + (graph.drones_count * 5)

    def reconstruct_path(
            self,
            memory: dict[tuple[str , int], tuple[str, int]],
            end_state: tuple[str, int]
    ) -> list[tuple[str, int]]:
        path = []
        current: Optional[tuple[str, int]] = end_state

        while current is not None:
            path.append(current)
            current = memory.get(current)

        path.reverse()
        return path

    def find_path(self, start_name: str, end_name: str, start_turn: int) -> list[tuple[str, int]]:
        """
        Finds the fastest valid route for a single drone, actively avoiding
        future traffic jams using the ReservationTable.
        """
        # Queue format: (turn, tie_breaker, current_node_name)
        queue: list[tuple[int, int, str]] = []
        tie_breaker = itertools.count()  # The Pythonic fix for the heapq crash!

        heapq.heappush(queue, (start_turn, next(tie_breaker), start_name))

        # memory maps: (node_name, turn) -> (came_from_name, came_from_turn)
        memory: dict[tuple[str, int], tuple[str, int]] = {}
        visited: set[tuple[str, int]] = set()

        while queue:
            curr_turn, _, curr_name = heapq.heappop(queue)

            if curr_turn > self.max_turn_limit:
                continue

            if curr_name == end_name:
                return self.reconstruct_path(memory, (curr_name, curr_turn))

            state = (curr_name, curr_turn)
            if state in visited:
                continue
            visited.add(state)

            curr_node = self.graph.nodes[curr_name]

            # ACTION 1: Wait in the current zone
            next_turn = curr_turn + 1
            if self.reservations.can_occupy_node(curr_name, next_turn):
                if (curr_name, next_turn) not in visited:
                    memory[(curr_name, next_turn)] = state
                    heapq.heappush(queue, (next_turn, next(tie_breaker), curr_name))

            # ACTION 2: Move to a neighboring zone
            for edge in curr_node.edges:
                neighbor_node = self.graph.nodes[edge.target]
                arrival_turn = curr_turn + neighbor_node.cost

                if arrival_turn > self.max_turn_limit:
                    continue

                # Rule 1: The room must have space when we arrive
                if not self.reservations.can_occupy_node(edge.target, arrival_turn):
                    continue

                # Rule 2: The connection must have space for the entire travel duration
                edge_is_clear = True
                for t in range(curr_turn, arrival_turn):
                    if not self.reservations.can_traverse_edge(curr_name, edge.target, edge.capacity, t):
                        edge_is_clear = False
                        break

                if edge_is_clear and (edge.target, arrival_turn) not in visited:
                    memory[(edge.target, arrival_turn)] = state
                    heapq.heappush(queue, (arrival_turn, next(tie_breaker), edge.target))

        return []  # No path found
