"""Planar differential-track steering in Webots' default ENU world frame."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TrackCommand:
    left: float
    right: float
    distance: float
    arrived: bool


def approach_command(
    position_xy: tuple[float, float],
    yaw: float,
    target_xy: tuple[float, float],
    *,
    stop_distance: float = 0.50,
    arrival_tolerance: float = 0.08,
    max_speed: float = 3.0,
    turn_speed: float = 1.7,
    heading_tolerance: float = 0.18,
) -> TrackCommand:
    """Return left/right wheel speeds using X/Y as the ground plane."""
    dx = target_xy[0] - position_xy[0]
    dy = target_xy[1] - position_xy[1]
    distance = math.hypot(dx, dy)
    if distance <= stop_distance + arrival_tolerance:
        return TrackCommand(0.0, 0.0, distance, True)

    desired_yaw = math.atan2(dy, dx)
    error = math.atan2(math.sin(desired_yaw - yaw), math.cos(desired_yaw - yaw))
    if abs(error) > heading_tolerance:
        direction = 1.0 if error > 0.0 else -1.0
        return TrackCommand(-direction * turn_speed, direction * turn_speed, distance, False)

    speed = min(max_speed, 0.7 + distance * 0.55)
    return TrackCommand(speed, speed, distance, False)
