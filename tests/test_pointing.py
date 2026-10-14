import unittest

from core.pointing import ImagePoint, select_pointed_target


class PointingSelectionTests(unittest.TestCase):
    def test_selects_target_aligned_with_finger(self):
        result = select_pointed_target(
            (20, 50), (50, 50),
            [ImagePoint("target-A", 120, 52), ImagePoint("target-B", 90, 105)],
        )
        self.assertEqual(result.target, "target-A")
        self.assertEqual(result.reason, "selected")

    def test_rejects_target_behind_finger(self):
        result = select_pointed_target(
            (20, 50), (50, 50), [ImagePoint("target-A", 10, 50)]
        )
        self.assertIsNone(result.target)

    def test_rejects_missing_or_short_gesture(self):
        self.assertEqual(
            select_pointed_target(None, (50, 50), []).reason,
            "gesture_not_visible",
        )
        self.assertEqual(
            select_pointed_target((20, 50), (25, 50), []).reason,
            "gesture_too_short",
        )

    def test_rejects_no_aligned_target(self):
        result = select_pointed_target(
            (20, 50), (50, 50), [ImagePoint("target-A", 50, 140)]
        )
        self.assertEqual(result.reason, "no_target_aligned_with_gesture")

    def test_rejects_ambiguous_targets(self):
        result = select_pointed_target(
            (20, 50), (50, 50),
            [ImagePoint("target-A", 150, 50), ImagePoint("target-B", 150, 52)],
        )
        self.assertEqual(result.reason, "ambiguous_pointing")


if __name__ == "__main__":
    unittest.main()
