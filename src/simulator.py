from src.graph import Graph
from src.space_time_pathfinder import PathFinder


class Simulator:
    """
    Executes the Multi-Agent Path Finding (MAPF) simulation,
    orchestrates the drones, and formats the turn-by-turn output.
    """

    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.pathfinder = PathFinder(graph)

        # Stores the calculated route for each drone. Map: drone_id -> path
        self.drone_paths: dict[int, list[tuple[str, int]]] = {}
        self.max_turn: int = 0

    def run(self) -> bool:
        """Calculates and reserves cooperative paths for all drones."""
        for drone_id in range(1, self.graph.drones_count + 1):

            path = self.pathfinder.find_path(
                start_name=self.graph.start_node.name,
                end_name=self.graph.end_node.name,
                start_turn=0
            )

            if not path:
                print(f"Error: Drone {drone_id} is completely trapped. No path found.")
                return False

            # Lock the path in the ReservationTable so the next drone routes around it
            self.pathfinder.reservations.reserve_path(path)
            self.drone_paths[drone_id] = path

            # Track the longest journey so we know when to end the simulation loop
            final_arrival_turn = path[-1][1]
            if final_arrival_turn > self.max_turn:
                self.max_turn = final_arrival_turn

        return True

    def print_simulation(self) -> None:
        """
        Loops through time (turn 1 to max_turn) and prints the movements
        strictly following the 42 subject formatting rules.
        """
        for current_turn in range(1, self.max_turn + 1):
            moves_this_turn: list[str] = []

            for drone_id, path in self.drone_paths.items():
                prev_node = None
                curr_node = None
                curr_turn_in_path = -1

                # Find exactly where this drone is during 'current_turn'
                for i in range(len(path)):
                    if path[i][1] == current_turn:
                        curr_node = path[i][0]
                        curr_turn_in_path = path[i][1]
                        if i > 0:
                            prev_node = path[i-1][0]
                        break
                    elif path[i][1] > current_turn:
                        # The drone is mid-flight (heading to a restricted zone)
                        curr_node = path[i][0]
                        curr_turn_in_path = path[i][1]
                        prev_node = path[i-1][0]
                        break

                # If the drone has already finished its journey, ignore it
                if curr_node is None or prev_node is None:
                    continue

                if curr_turn_in_path == current_turn:
                    # The drone safely arrived at a node.
                    # Rule: Stationary drones are omitted from the line.
                    if prev_node != curr_node:
                        moves_this_turn.append(f"D{drone_id}-{curr_node}")
                else:
                    # The drone is mid-flight towards a restricted zone (cost = 2).
                    # Rule: Print D<ID>-<connection> in case of drones still in flight.
                    moves_this_turn.append(f"D{drone_id}-{prev_node}-{curr_node}")

            # Only print the line if at least one drone actually moved this turn
            if moves_this_turn:
                print(" ".join(moves_this_turn))
