import math
import unittest

from core.viewpoint import look_at_orientation, rotate_vector


class ViewpointTests(unittest.TestCase):
    def assert_camera_faces(self, position, target, up_hint=(0.0, 0.0, 1.0)):
        rotation = look_at_orientation(position, target, up_hint)
        forward = rotate_vector((0.0, 0.0, -1.0), rotation)
        expected = tuple(target[i] - position[i] for i in range(3))
        length = math.sqrt(sum(value * value for value in expected))
        expected = tuple(value / length for value in expected)
        self.assertAlmostEqual(sum(a * b for a, b in zip(forward, expected)), 1.0, places=6)
        self.assertAlmostEqual(math.sqrt(sum(value * value for value in rotation[:3])), 1.0, places=6)

    def test_overview_and_robot_views_face_their_targets(self):
        self.assert_camera_faces((4.5, -6.2, 4.1), (0.0, 0.0, 0.55))
        self.assert_camera_faces((-2.85, -2.65, 1.12), (-1.7, -1.1, 0.37))

    def test_overhead_view_handles_parallel_up_direction(self):
        self.assert_camera_faces((0.0, -0.1, 7.0), (0.0, -0.1, 0.0), (0.0, -1.0, 0.0))

    def test_rejects_camera_and_target_at_same_position(self):
        with self.assertRaises(ValueError):
            look_at_orientation((1.0, 1.0, 1.0), (1.0, 1.0, 1.0))


if __name__ == "__main__":
    unittest.main()
