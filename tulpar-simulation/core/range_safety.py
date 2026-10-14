"""Fail-safe interpretation of the simulated front range sensor."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RangeDecision:
    status: str
    distance_m: float | None


class RangeSafetyMonitor:
    """Retry one invalid sample, stop on a second, and stop for near obstacles."""

    def __init__(self):
        self.consecutive_invalid = 0

    def evaluate(self, reading_m: float, *, max_range_m: float, stop_distance_m: float) -> RangeDecision:
        if not math.isfinite(reading_m) or reading_m < 0.0 or reading_m > max_range_m:
            self.consecutive_invalid += 1
            if self.consecutive_invalid == 1:
                return RangeDecision("retry", None)
            return RangeDecision("sensor_fault", None)

        self.consecutive_invalid = 0
        if reading_m <= stop_distance_m:
            return RangeDecision("obstacle", reading_m)
        return RangeDecision("clear", reading_m)
