"""Deterministic face animation timing for the phone display."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class EyePose:
    left_open: float
    right_open: float
    pupil_x: float
    pupil_y: float


def _blink(time_s: float, period_s: float = 4.6, offset_s: float = 0.7) -> float:
    phase = (time_s + offset_s) % period_s
    duration = 0.16
    if phase >= duration:
        return 1.0
    # Close and reopen smoothly within the short blink interval.
    return abs((phase / duration) * 2.0 - 1.0)


def eye_pose(emotion: str, time_s: float) -> EyePose:
    """Return eye openness and gaze offsets in a normalised range."""
    baseline = {
        "neutral": 0.92,
        "happy": 0.86,
        "sad": 0.70,
        "surprised": 1.0,
        "angry": 0.82,
        "sleepy": 0.38,
        "wink": 0.92,
        "love": 0.86,
        "thinking": 0.90,
    }.get(emotion, 0.92)
    blink = _blink(time_s)
    left_open = baseline * blink
    right_open = baseline * blink
    if emotion == "wink":
        wink_phase = (time_s + 0.4) % 2.8
        if wink_phase < 0.24:
            wink_open = abs((wink_phase / 0.24) * 2.0 - 1.0)
            left_open = 0.12 + 0.80 * wink_open
    gaze_x = 0.0
    gaze_y = 0.0
    if emotion == "thinking":
        gaze_x, gaze_y = 0.35, -0.32
    elif emotion == "sad":
        gaze_y = 0.28
    else:
        gaze_x = 0.08 * math.sin(time_s * 0.8)
    return EyePose(left_open, right_open, gaze_x, gaze_y)
