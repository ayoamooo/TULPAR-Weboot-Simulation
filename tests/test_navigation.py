import math
import unittest

from core.navigation import approach_command


class NavigationTests(unittest.TestCase):
    def test_ground_plane_uses_x_and_y(self):
        command = approach_command((0.0, 0.0), 0.0, (2.0, 0.0))
        self.assertFalse(command.arrived)
        self.assertGreater(command.left, 0.0)
        self.assertEqual(command.left, command.right)

    def test_turns_toward_positive_y_target(self):
        command = approach_command((0.0, 0.0), 0.0, (0.0, 2.0))
        self.assertLess(command.left, 0.0)
        self.assertGreater(command.right, 0.0)

    def test_stops_at_approach_distance(self):
        command = approach_command((0.0, 0.0), math.pi, (0.55, 0.0))
        self.assertTrue(command.arrived)
        self.assertEqual((command.left, command.right), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
