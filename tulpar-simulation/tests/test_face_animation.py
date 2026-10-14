import unittest

from core.face_animation import eye_pose


class FaceAnimationTests(unittest.TestCase):
    def test_neutral_face_blinks_periodically(self):
        self.assertGreater(eye_pose("neutral", 1.0).left_open, 0.8)
        blink = eye_pose("neutral", 3.98)
        self.assertLess(blink.left_open, 0.1)
        self.assertEqual(blink.left_open, blink.right_open)

    def test_sleepy_and_thinking_have_distinct_expression_motion(self):
        sleepy = eye_pose("sleepy", 1.0)
        thinking = eye_pose("thinking", 1.0)
        self.assertLess(sleepy.left_open, thinking.left_open)
        self.assertGreater(thinking.pupil_x, 0.0)
        self.assertLess(thinking.pupil_y, 0.0)

    def test_wink_is_asymmetric(self):
        pose = eye_pose("wink", 2.5)
        self.assertNotEqual(pose.left_open, pose.right_open)


if __name__ == "__main__":
    unittest.main()
