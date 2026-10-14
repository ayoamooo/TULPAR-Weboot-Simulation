"""Select a visible scene marker from a simulated operator pointing ray.

The inputs are camera image coordinates from Webots recognition objects. This is
geometric simulated perception; it is not a learned human-pose detector.
"""

from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class ImagePoint:
    label: str
    x: float
    y: float


@dataclass(frozen=True)
class PointingSelection:
    target: str | None
    angular_error_deg: float | None
    reason: str


def select_pointed_target(
    shoulder: tuple[float, float] | None,
    fingertip: tuple[float, float] | None,
    targets: Iterable[ImagePoint],
    *,
    max_angular_error_deg: float = 8.0,
    min_gesture_length_px: float = 12.0,
    min_target_distance_px: float = 18.0,
    ambiguity_margin_deg: float = 2.0,
) -> PointingSelection:
    """Pick a target aligned with the shoulder-to-fingertip image ray.

    Reject missing or weak gestures, targets behind the finger, and near ties.
    Coordinates use the camera image frame; the function is independent of Webots.
    """
    if shoulder is None or fingertip is None:
        return PointingSelection(None, None, "gesture_not_visible")

    dx = fingertip[0] - shoulder[0]
    dy = fingertip[1] - shoulder[1]
    gesture_length = math.hypot(dx, dy)
    if gesture_length < min_gesture_length_px:
        return PointingSelection(None, None, "gesture_too_short")

    gesture_angle = math.atan2(dy, dx)
    candidates: list[tuple[float, str]] = []
    for target in targets:
        # Extend the shoulder-to-fingertip ray; the target lies beyond the hand.
        tx = target.x - shoulder[0]
        ty = target.y - shoulder[1]
        distance = math.hypot(tx, ty)
        if distance < min_target_distance_px:
            continue
        target_angle = math.atan2(ty, tx)
        error = math.atan2(
            math.sin(target_angle - gesture_angle),
            math.cos(target_angle - gesture_angle),
        )
        error_deg = abs(math.degrees(error))
        if error_deg <= max_angular_error_deg:
            candidates.append((error_deg, target.label))

    if not candidates:
        return PointingSelection(None, None, "no_target_aligned_with_gesture")
    candidates.sort()
    if len(candidates) > 1 and candidates[1][0] - candidates[0][0] < ambiguity_margin_deg:
        return PointingSelection(None, candidates[0][0], "ambiguous_pointing")
    return PointingSelection(candidates[0][1], candidates[0][0], "selected")
