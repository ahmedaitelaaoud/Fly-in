import sys
import pygame

from src.parser import MapParser
from src.simulator import Simulator

# --- 1337 Dark Theme Palette ---
BG_COLOR = (43, 50, 64)          # Deep slate
NODE_COLOR = (90, 104, 133)      # Muted blue
EDGE_COLOR = (178, 182, 224)     # Light periwinkle
START_COLOR = (50, 205, 50)      # Lime green
END_COLOR = (220, 20, 60)        # Crimson
DRONE_COLOR = (34, 211, 238)     # Cyan
TEXT_COLOR = (248, 250, 252)     # Off-white

WIDTH, HEIGHT = 1024, 768
FPS = 60


def visualize_pygame(parser: MapParser, simulator: Simulator) -> None:
    """
    Renders an interactive Pygame visualization of the drone routing.
    Includes dynamic coordinate scaling and playback controls.
    """
    # Initialize the Pygame engine
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Fly-in Simulation (Pygame Engine)")
    clock = pygame.time.Clock()

    # Setup Fonts gracefully (fallback to default if Consolas is missing)
    try:
        font = pygame.font.SysFont("consolas", 14, bold=True)
        title_font = pygame.font.SysFont("consolas", 24, bold=True)
    except:
        font = pygame.font.Font(None, 24)
        title_font = pygame.font.Font(None, 36)

    # =========================================================================
    # DYNAMIC MAP SCALING LOGIC
    # =========================================================================
    # We need to map arbitrary (x, y) coordinates to fit the 1024x768 screen.
    xs = [z.x for z in parser.zones.values()]
    ys = [z.y for z in parser.zones.values()]

    # Handle single-node edge cases safely
    min_x, max_x = (min(xs), max(xs)) if xs else (0, 0)
    min_y, max_y = (min(ys), max(ys)) if ys else (0, 0)

    range_x = max(max_x - min_x, 1)  # Prevent division by zero
    range_y = max(max_y - min_y, 1)

    padding = 100

    def get_screen_xy(name: str) -> tuple[int, int]:
        """Converts raw map coordinates to screen pixel coordinates."""
        z = parser.zones[name]
        screen_x = padding + (z.x - min_x) / range_x * (WIDTH - 2 * padding)
        # Invert Y so positive Y goes "up" the screen mathematically
        screen_y = HEIGHT - padding - (z.y - min_y) / range_y * (HEIGHT - 2 * padding)
        return int(screen_x), int(screen_y)

    # Pre-calculate screen positions for all zones for $O(1)$ fast rendering
    pos = {name: get_screen_xy(name) for name in parser.zones.keys()}

    # =========================================================================
    # SIMULATION STATE
    # =========================================================================
    current_turn = 0
    max_turn = simulator.max_turn
    playing = False
    last_step_time = pygame.time.get_ticks()
    STEP_DELAY = 600  # Milliseconds per turn when auto-playing

    # =========================================================================
    # MAIN EVENT LOOP
    # =========================================================================
    running = True
    while running:
        # 1. Handle Events (Controls)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_RIGHT and current_turn < max_turn:
                    current_turn += 1
                    playing = False
                elif event.key == pygame.K_LEFT and current_turn > 0:
                    current_turn -= 1
                    playing = False
                elif event.key in (pygame.K_0, pygame.K_r):
                    current_turn = 0
                    playing = False

        # 2. Handle Auto-Playback Timers
        if playing:
            now = pygame.time.get_ticks()
            if now - last_step_time > STEP_DELAY:
                if current_turn < max_turn:
                    current_turn += 1
                    last_step_time = now
                else:
                    playing = False  # Stop playing automatically when we hit the end

        # 3. Draw Background
        screen.fill(BG_COLOR)

        # 4. Draw Edges (Hallways)
        for conn in parser.connections:
            x1, y1 = pos[conn.zone1]
            x2, y2 = pos[conn.zone2]

            # Draw connecting line
            pygame.draw.line(screen, EDGE_COLOR, (x1, y1), (x2, y2), 3)

            # Draw connection capacity hovering over the middle of the line
            mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
            cap_surf = font.render(str(conn.max_link_capacity), True, (255, 100, 100))
            cap_rect = cap_surf.get_rect(center=(mid_x, mid_y - 15))
            screen.blit(cap_surf, cap_rect)

        # 5. Draw Zones (Nodes)
        for name, zone in parser.zones.items():
            x, y = pos[name]

            # Determine Node Color
            color = NODE_COLOR
            if name == parser.start_zone_name:
                color = START_COLOR
            elif name == parser.end_zone_name:
                color = END_COLOR

            # Draw Node Circle and its dark border
            pygame.draw.circle(screen, color, (x, y), 25)
            pygame.draw.circle(screen, (20, 20, 20), (x, y), 25, 3)

            # Draw Zone Name and Max Drones beneath the node
            label = f"{name} (c:{zone.max_drones})"
            lbl_surf = font.render(label, True, TEXT_COLOR)
            lbl_rect = lbl_surf.get_rect(center=(x, y + 40))

            # Small background box for text readability
            bg_rect = lbl_rect.inflate(10, 4)
            pygame.draw.rect(screen, (30, 30, 30), bg_rect, border_radius=4)
            screen.blit(lbl_surf, lbl_rect)

        # 6. Calculate exactly where drones are right now (Time-Space logic)
        groups: dict[str, list[int]] = {}
        for d_id, path in simulator.drone_paths.items():
            if not path:
                continue

            # Scan the drone's timeline backward to find its last known location
            current_loc = path[0][0]
            for loc, t in reversed(path):
                if t <= current_turn:
                    current_loc = loc
                    break

            groups.setdefault(current_loc, []).append(d_id)

        # 7. Draw Drones on top of the Nodes
        for loc, drones in groups.items():
            x, y = pos[loc]

            # Draw a cyan marker for the drones
            pygame.draw.circle(screen, DRONE_COLOR, (x, y - 10), 12)
            pygame.draw.circle(screen, (0, 0, 0), (x, y - 10), 12, 2)

            # Stack drones gracefully: Write "D1" or "D1 + 2" if multiple drones are in the same room
            lbl = f"D{drones[0]}" + (f"+{len(drones)-1}" if len(drones) > 1 else "")
            drone_lbl = font.render(lbl, True, (0, 0, 0))
            drone_rect = drone_lbl.get_rect(center=(x, y - 10))
            screen.blit(drone_lbl, drone_rect)

        # 8. Draw UI/Controls Header
        status = "PLAYING" if playing else "PAUSED"
        header = f"Turn {current_turn} / {max_turn}  |  [{status}]"
        header_surf = title_font.render(header, True, TEXT_COLOR)
        screen.blit(header_surf, (20, 20))

        controls = "Controls: [SPACE] Play/Pause | [RIGHT/LEFT] Step Turn | [R/0] Reset"
        ctrl_surf = font.render(controls, True, (150, 160, 180))
        screen.blit(ctrl_surf, (20, 50))

        # 9. Render Screen & Tick Clock
        pygame.display.flip()
        clock.tick(FPS)

    # Ensure a clean exit without hanging
    pygame.quit()
