import unittest

from core.pointing import (
    ImagePoint,
    recognized_world_target,
    select_pointed_target,
    update_selection_success,
)


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

    def test_rejected_attempt_does_not_prevent_a_later_correct_selection(self):
        status = update_selection_success(None, "target-A", None)
        self.assertIsNone(status)
        status = update_selection_success(status, "target-A", "target-A")
        self.assertTrue(status)

    def test_latest_accepted_selection_determines_trial_selection_status(self):
        status = update_selection_success(None, "target-A", "target-B")
        self.assertFalse(status)
        status = update_selection_success(status, "target-A", None)
        self.assertFalse(status)
        status = update_selection_success(status, "target-A", "target-A")
        self.assertTrue(status)

    def test_operator_target_requires_a_visible_camera_label(self):
        self.assertIsNone(
            recognized_world_target({}, "operator-torso", (1.45, -1.1, 0.0))
        )
        self.assertEqual(
            recognized_world_target(
                {"operator-torso": (320.0, 240.0)},
                "operator-torso",
                (1.45, -1.1, 0.0),
            ),
            (1.45, -1.1),
        )

    def test_visible_target_requires_finite_world_coordinates(self):
        with self.assertRaises(ValueError):
            recognized_world_target(
                {"operator-torso": (10.0, 20.0)},
                "operator-torso",
                (float("nan"), -1.1, 0.0),
            )


if __name__ == "__main__":
    unittest.main()
