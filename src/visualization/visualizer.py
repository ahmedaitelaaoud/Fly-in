from src.models.zone import Zone
from src.graph.graph import Graph


class TerminalVisualizer:
    """Handles terminal output and visualization using ANSI codes."""

    # ANSI color codes mapped from string names
    COLORS = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "black": "\033[30m",
        "reset": "\033[0m",
        "bold": "\033[1m"
    }

    def print_simulation(
        self,
        graph: Graph,
        all_paths: list[list[tuple[Zone, int]]],
        total_turns: int,
    ) -> None:
        """
        Print the complete simulation turn by turn, displaying both
        the state of the drones and the exact movement commands.
        """
        movements_by_turn: dict[int, list[str]] = {}

        # Precompute exact turn movements
        for drone_id, path in enumerate(all_paths, start=1):
            for i, (zone, turn) in enumerate(path):
                if i == 0:
                    continue

                prev_zone, _ = path[i - 1]
                if zone == prev_zone:
                    continue

                if zone.get_movement_cost() == 2:
                    if turn - 1 not in movements_by_turn:
                        movements_by_turn[turn - 1] = []
                    movements_by_turn[turn - 1].append(
                        f"D{drone_id}-{prev_zone.name}-{zone.name}"
                    )

                if turn not in movements_by_turn:
                    movements_by_turn[turn] = []
                movements_by_turn[turn].append(f"D{drone_id}-{zone.name}")

        # Precompute drone positions by turn
        drones_positions: dict[int, dict[int, Zone]] = {
            t: {} for t in range(total_turns + 1)
        }

        for drone_id, path in enumerate(all_paths, start=1):
            current_idx = 0
            for turn in range(0, total_turns + 1):
                while (current_idx + 1 < len(path) and
                       path[current_idx + 1][1] <= turn):
                    current_idx += 1
                drones_positions[turn][drone_id] = path[current_idx][0]

        # Print initial state (Turn 0)
        self.print_turn_state(0, graph, drones_positions[0])

        for turn in range(1, total_turns + 1):
            movements = movements_by_turn.get(turn, [])
            # Print movements in exact required format
            self.print_turn_movements(turn, movements)
            # Print visual state
            self.print_turn_state(turn, graph, drones_positions[turn])

        self.print_summary(total_turns)

    def print_turn_movements(self, turn: int, movements: list[str]) -> None:
        """Prints the movements for the turn in the required format."""
        if movements:
            print(' '.join(movements))

    def print_turn_state(
        self, turn: int, graph: Graph, drone_positions: dict[int, Zone]
    ) -> None:
        """Visualizes the map and drones for a turn using ANSI colors."""
        print(f"\n{self.COLORS['bold']}=== Turn {turn} "
              f"State ==={self.COLORS['reset']}")

        zone_drones: dict[str, list[int]] = {
            zone.name: [] for zone in graph.zones.values()
        }
        for drone_id, zone in drone_positions.items():
            zone_drones[zone.name].append(drone_id)

        for zone in graph.zones.values():
            color_name = zone.color.lower() if zone.color else "white"
            color_code = self.COLORS.get(color_name, self.COLORS['white'])
            drones_here = zone_drones[zone.name]

            zone_str = f"{color_code}[{zone.name}]{self.COLORS['reset']}"

            if drones_here:
                drones_str = (
                    f" {self.COLORS['cyan']}🚁 Drones: "
                    + ", ".join(f"D{d}" for d in drones_here)
                    + self.COLORS['reset']
                )
            else:
                drones_str = ""

            print(f"{zone_str}{drones_str}")
        print("-" * 30 + "\n")

    def print_summary(self, total_turns: int) -> None:
        """Print the total number of turns required."""
        print(f"{self.COLORS['bold']}{self.COLORS['green']}Simulation "
              f"finished in {total_turns} turns!{self.COLORS['reset']}")
