import sys

from src.custom_errors import ParsingErrors
from src.graph import Graph
from src.parser import MapParser
from src.simulator import Simulator


def main() -> None:
    # Safely parse command line arguments
    args = sys.argv[1:]

    # Check for the visualization flag
    visualize = "--visualize" in args or "-v" in args

    # Filter out flags to find the actual map filepath
    filepaths = [arg for arg in args if not arg.startswith("-")]

    if len(filepaths) != 1:
        print("Usage: python3 main.py <map_file.txt> [--visualize]")
        sys.exit(1)

    filepath = filepaths[0]

    try:
        # Phase 1: Parse and Validate
        parser = MapParser(filepath)
        parser.parse()

        # Phase 2: Build the Graph Engine
        graph = Graph(parser)

        # Phase 3: Run the Time-Space Simulation
        simulator = Simulator(graph)

        if simulator.run():
            # Phase 4: Print the Results (Terminal)
            simulator.print_simulation()

            # Phase 5: Interactive Visualizer
            if visualize:
                from src.visualizer import visualize_pygame
                print("\n[🎮] Launching Pygame Engine...")
                visualize_pygame(parser, simulator)

    except ParsingErrors as e:
        print(f"{e}")
        sys.exit(1)
    except Exception as e:
        print(f"Critical Crash: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
