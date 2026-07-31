import pygame

from src.graph.graph import Graph
from src.models.drone import Drone
from src.models.zone import Zone, ZoneType


class Visualizer:
    """
    Pygame visualizer for the Fly-in simulation.

    Args:
        graph: Simulation graph.
        drones: List of drones.
        total_turns: Total number of turns in the simulation.

    Features:
        - Draws all zones and connections.
        - Draws drones.
        - Displays drones travelling on connections.
        - Camera movement.
        - Turn-by-turn simulation.
        - Auto play mode.
    """

    def __init__(self,
                 graph: Graph,
                 drones: list[Drone],
                 total_turns: int) -> None:
        """
        Initialize the visualizer.

        Args:
            graph: Simulation graph.
            drones: List of drones.
        """
        pygame.init()

        self.graph = graph
        self.drones = drones
        self.total_turns = total_turns

        self.width = 1700
        self.height = 900

        self.screen = pygame.display.set_mode((self.width, self.height))

        pygame.display.set_caption("Fly-in")

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 14)

        self.current_turn = 0

        self.auto_play = False
        self.auto_timer = 0
        self.auto_delay = 500

        # Camera
        self.camera_x = 0
        self.camera_y = 0

        self.offset_x = self.width // 2
        self.offset_y = self.height // 2

        self.scale = 100

    def to_screen(self, x: float, y: float) -> tuple[int, int]:
        """
        Convert world coordinates to screen coordinates.

        Args:
            x: World x coordinate.
            y: World y coordinate.

        Returns:
            Screen coordinates.
        """
        screen_x = self.offset_x + x * self.scale
        screen_y = self.offset_y - y * self.scale

        return (int(screen_x), int(screen_y))

    def get_zone_color(self, zone: Zone) -> pygame.Color:
        """
        Return the display color for a zone.

        Args:
            zone: Zone to color.

        Returns:
            pygame.Color object.
        """
        if zone.color is not None:
            try:
                return pygame.Color(zone.color)
            except ValueError:
                pass

        if zone.is_start or zone.is_end:
            return pygame.Color("green")
        if zone.zone_type == ZoneType.RESTRICTED:
            return pygame.Color("purple")
        if zone.zone_type == ZoneType.PRIORITY:
            return pygame.Color("cyan")
        if zone.zone_type == ZoneType.BLOCKED:
            return pygame.Color("gray")
        return pygame.Color("dodgerblue")

    def get_drone_position(
        self, drone: Drone
    ) -> tuple[Zone | None, tuple[Zone, Zone] | None]:
        """
        Calculate the drone's position for the current turn.
        Returns (current_zone, connection).
        """
        if not drone.path:
            return None, None

        current_zone = drone.path[0][0]
        connection = None

        for i in range(1, len(drone.path)):
            previous_zone, _ = drone.path[i - 1]
            next_zone, arrival_turn = drone.path[i]
            movement_cost = next_zone.get_movement_cost()

            if movement_cost == 2 and self.current_turn == arrival_turn - 1:
                return None, (previous_zone, next_zone)

            if arrival_turn <= self.current_turn:
                current_zone = next_zone
            else:
                break

        return current_zone, connection

    def draw_connections(self) -> None:
        """
        Draw every graph connection.
        """
        for connection in self.graph.connections:
            ax, ay = self.to_screen(connection.zone_a.x, connection.zone_a.y)
            bx, by = self.to_screen(connection.zone_b.x, connection.zone_b.y)
            pygame.draw.line(
                self.screen, pygame.Color("gray"),
                (ax + self.camera_x, ay + self.camera_y),
                (bx + self.camera_x, by + self.camera_y), 3)

    def draw_zones(self) -> None:
        """
        Draw every zone.
        """
        for zone in self.graph.zones.values():

            x, y = self.to_screen(zone.x, zone.y)

            x += self.camera_x
            y += self.camera_y

            pygame.draw.circle(
                self.screen,
                self.get_zone_color(zone),
                (x, y), 16)

            pygame.draw.circle(
                self.screen,
                pygame.Color("black"),
                (x, y), 16, 2)

            if self.scale > 70:
                text = self.font.render(
                    zone.name,
                    True,
                    pygame.Color("white"))

                rect = text.get_rect(center=(x, y - 30))
                self.screen.blit(text, rect)

    def draw_drones(self) -> None:
        """
        Draw every drone.

        A drone is drawn:
            - At its current zone.
            - At the middle of a connection while travelling toward a
            restricted zone.
        """
        for drone in self.drones:
            current_zone, connection = self.get_drone_position(drone)

            # Drone is travelling
            if connection is not None:
                zone_a, zone_b = connection
                x1, y1 = self.to_screen(zone_a.x, zone_a.y)
                x2, y2 = self.to_screen(zone_b.x, zone_b.y)
                x = (x1 + x2) // 2
                y = (y1 + y2) // 2
            # Drone is inside a zone
            elif current_zone is not None:
                x, y = self.to_screen(
                    current_zone.x, current_zone.y)
            else:
                continue
            x += self.camera_x
            y += self.camera_y
            pygame.draw.circle(
                self.screen,
                pygame.Color("white"),
                (x, y), 7)
            pygame.draw.circle(
                self.screen,
                pygame.Color("black"),
                (x, y), 7, 1)
            text = self.font.render(
                str(drone.drone_id),
                True,
                pygame.Color("black"))
            rect = text.get_rect(center=(x, y))
            self.screen.blit(text, rect)

    def draw(self) -> None:
        """
        Draw one simulation frame.
        """
        self.screen.fill(pygame.Color(25, 25, 35))
        self.draw_connections()
        self.draw_zones()
        self.draw_drones()
        text = self.font.render(
            f"Turn {self.current_turn} / {self.total_turns}",
            True,
            pygame.Color("white"))
        self.screen.blit(text, (10, 10))
        pygame.display.flip()

    def _handle_keydown(self, key: int) -> None:
        """
        Handle keyboard input.

        Args:
            key: Pygame key code.
        """
        if key == pygame.K_SPACE:
            if self.current_turn < self.total_turns:
                self.current_turn += 1
        elif key == pygame.K_a:
            self.auto_play = not self.auto_play
        elif key == pygame.K_RIGHT:
            self.camera_x += 50
        elif key == pygame.K_LEFT:
            self.camera_x -= 50
        elif key == pygame.K_UP:
            self.camera_y += 50
        elif key == pygame.K_DOWN:
            self.camera_y -= 50

    def _update_auto_play(self, dt: int) -> None:
        """
        Advance the simulation automatically.

        Args:
            dt: Milliseconds since the previous frame.
        """
        if not self.auto_play:
            return
        self.auto_timer += dt
        if self.auto_timer < self.auto_delay:
            return
        self.auto_timer = 0
        if self.current_turn < self.total_turns:
            self.current_turn += 1
        else:
            self.auto_play = False

    def run(self) -> None:
        """
        Start the visualizer.
        """
        running = True
        while running:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event.key)
            self._update_auto_play(dt)
            self.draw()
        pygame.quit()
