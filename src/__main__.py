import sys

from src.parser.map_parser import parse_file, ParseError
from src.graph.graph import Graph
from src.models.zone import Zone
from src.models.drone import Drone
from src.pathfinding.pathfinder import Pathfinder
from src.simulation.simulator import ReservationTable
from src.visualization.visualizer import VisualizerPrint
from src.visualization.pg_visualizer import Visualizer


def main() -> None:
    """
    Run the Fly-in simulation.

    Parses the input map, computes reservation-aware paths for all
    drones, prints the simulation in the terminal, and launches the
    pygame visualizer.
    """
    if len(sys.argv) != 2:
        print("Usage: make run MAP=<map_file>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        data = parse_file(filename)
    except ParseError as e:
        print(f"[ERROR]: {e}")
        sys.exit(1)
    # print(""*10)
    # print(vars(data))
    # print(""*10)
    graph = Graph(data.zones, data.connections)
    reservations = ReservationTable(graph)
    pathfinder = Pathfinder()
    visualizer = VisualizerPrint()

    total_turns = 0
    all_paths: list[list[tuple[Zone, int]]] = []

    for drone_id in range(1, data.nb_drones + 1):
        path = pathfinder.find_path(
            graph,
            data.start_zone,
            data.end_zone,
            data.nb_drones,
            reservations
        )

        if not path:
            print(f"Drone {drone_id}: No path found")
            continue

        all_paths.append(path)

        finish_turn = path[-1][1]
        total_turns = max(total_turns, finish_turn)
        for i, (zone, turn) in enumerate(path):
            reservations.reserve(zone.name, turn)
            if i == 0:
                continue
            prev_zone, _ = path[i - 1]
            if zone == prev_zone:
                continue
            movement_cost = zone.get_movement_cost()
            for t in range(turn - movement_cost + 1, turn + 1):
                reservations.reserve_connection(
                    prev_zone.name,
                    zone.name,
                    t
                )

    if not all_paths:
        print("[ERROR]: No valid path found for any drone. "
              "The graph may be disconnected.")
        sys.exit(1)

    visualizer.print_simulation(all_paths, total_turns)

    # Create Drone objects for the pygame visualizer
    drones: list[Drone] = []

    for drone_id, drone_path in enumerate(all_paths, start=1):
        drone = Drone(
            drone_id=drone_id,
            path=drone_path,
        )
        drones.append(drone)

    # Launch pygame visualizer
    try:
        pg_visualizer = Visualizer(graph, drones, total_turns)
        pg_visualizer.run()
    except Exception as e:
        print(f"[INFO] Pygame visualization unavailable: {e}")


if __name__ == "__main__":
    main()
