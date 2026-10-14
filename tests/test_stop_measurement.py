import unittest

from core.stop_measurement import WheelStopDetector


class WheelStopDetectorTests(unittest.TestCase):
    def test_confirms_only_after_stable_wheel_samples(self):
        detector = WheelStopDetector(stable_samples=2)
        self.assertFalse(detector.update((0.0, 0.0, 0.0, 0.0), 0.0).stopped)
        self.assertFalse(detector.update((0.1, 0.1, 0.1, 0.1), 0.1).stopped)
        self.assertFalse(detector.update((0.2, 0.2, 0.2, 0.2), 0.2).stopped)
        self.assertFalse(detector.update((0.2, 0.2, 0.2, 0.2), 0.3).stopped)
        self.assertTrue(detector.update((0.2, 0.2, 0.2, 0.2), 0.4).stopped)

    def test_motion_resets_stability_window(self):
        detector = WheelStopDetector(stable_samples=2)
        detector.update((0.0,) * 4, 0.0)
        detector.update((0.0,) * 4, 0.1)
        detector.update((0.0,) * 4, 0.2)
        self.assertFalse(detector.update((1.0,) * 4, 0.3).stopped)
        self.assertFalse(detector.update((1.0,) * 4, 0.4).stopped)
        self.assertTrue(detector.update((1.0,) * 4, 0.5).stopped)

    def test_rejects_wrong_wheel_count_and_non_increasing_time(self):
        detector = WheelStopDetector()
        with self.assertRaises(ValueError):
            detector.update((0.0, 0.0), 0.0)
        detector.update((0.0,) * 4, 1.0)
        with self.assertRaises(ValueError):
            detector.update((0.0,) * 4, 1.0)


if __name__ == "__main__":
    unittest.main()
