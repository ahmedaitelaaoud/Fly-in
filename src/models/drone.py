from src.models.zone import Zone


class Drone:
    """Represents a delivery drone in the simulation.

    Args:
        drone_id: Unique identifier of the drone.
        path: Planned route as (zone, turn) pairs.

    Attributes:
        drone_id: Unique identifier of the drone.
        path: Planned route as (zone, turn) pairs.
    """

    def __init__(
        self,
        drone_id: int,
        path: list[tuple[Zone, int]] | None = None
    ) -> None:
        """
        Initialize a new Drone instance.
        Args:
            drone_id (int):
                Unique identifier of the drone.
            path (list[tuple[Zone, int]] | None):
                Planned route consisting of (zone, turn) pairs.
                Defaults to None.
        """
        self.drone_id = drone_id
        self.path = path if path is not None else []
