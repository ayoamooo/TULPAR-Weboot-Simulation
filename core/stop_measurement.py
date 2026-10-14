"""Estimate wheel angular speed from Webots position sensors."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StopSample:
    stopped: bool
    wheel_speeds: tuple[float, ...]


class WheelStopDetector:
    def __init__(self, wheel_count: int = 4, threshold_rad_s: float = 0.05, stable_samples: int = 3):
        if wheel_count < 1 or threshold_rad_s < 0.0 or stable_samples < 1:
            raise ValueError("wheel count and stable sample count must be positive; threshold cannot be negative")
        self.wheel_count = wheel_count
        self.threshold_rad_s = threshold_rad_s
        self.stable_samples = stable_samples
        self.previous_angles: tuple[float, ...] | None = None
        self.previous_time: float | None = None
        self.stable_count = 0

    def update(self, angles: tuple[float, ...], time_s: float) -> StopSample:
        if len(angles) != self.wheel_count:
            raise ValueError(f"expected {self.wheel_count} wheel angles, received {len(angles)}")
        if self.previous_time is not None and time_s <= self.previous_time:
            raise ValueError("sample time must increase")
        if self.previous_angles is None:
            self.previous_angles = angles
            self.previous_time = time_s
            return StopSample(False, tuple(0.0 for _ in angles))

        interval = time_s - self.previous_time
        speeds = tuple((angle - previous) / interval for angle, previous in zip(angles, self.previous_angles))
        self.previous_angles = angles
        self.previous_time = time_s
        if all(abs(speed) <= self.threshold_rad_s for speed in speeds):
            self.stable_count += 1
        else:
            self.stable_count = 0
        return StopSample(self.stable_count >= self.stable_samples, speeds)
