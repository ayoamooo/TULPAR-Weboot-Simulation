import unittest

from core.range_safety import RangeSafetyMonitor


class RangeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.monitor = RangeSafetyMonitor()

    def test_one_invalid_reading_is_retried_and_next_valid_recovers(self):
        self.assertEqual(
            self.monitor.evaluate(float("nan"), max_range_m=1.5, stop_distance_m=0.25).status,
            "retry",
        )
        self.assertEqual(
            self.monitor.evaluate(1.2, max_range_m=1.5, stop_distance_m=0.25).status,
            "clear",
        )

    def test_second_consecutive_invalid_reading_fails_safe(self):
        self.monitor.evaluate(float("inf"), max_range_m=1.5, stop_distance_m=0.25)
        self.assertEqual(
            self.monitor.evaluate(-1.0, max_range_m=1.5, stop_distance_m=0.25).status,
            "sensor_fault",
        )

    def test_near_obstacle_stops_but_max_range_is_clear(self):
        self.assertEqual(
            self.monitor.evaluate(0.20, max_range_m=1.5, stop_distance_m=0.25).status,
            "obstacle",
        )
        self.assertEqual(
            self.monitor.evaluate(1.5, max_range_m=1.5, stop_distance_m=0.25).status,
            "clear",
        )


if __name__ == "__main__":
    unittest.main()
