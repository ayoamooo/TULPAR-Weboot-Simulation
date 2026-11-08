import unittest

from core.command_policy import (
    CommandDecision,
    allow_action,
    explicit_navigation_target,
    is_scene_navigation_request,
    parse_spoken_command,
)
from core.scene_targets import validate_scene_navigation


class CommandPolicyTests(unittest.TestCase):
    def test_only_report_commands_start_floor_motion(self):
        self.assertEqual(parse_spoken_command("come to me").action, "approach_operator")
        self.assertEqual(parse_spoken_command("go to that marker").action, "conversation")
        self.assertEqual(parse_spoken_command("Could you drive anywhere you like?").action, "conversation")

    def test_stop_has_priority_in_every_mode(self):
        stop = parse_spoken_command("TULPAR, stop")
        self.assertEqual(stop, CommandDecision("stop"))
        self.assertTrue(allow_action(stop, "tabletop", True))

    def test_tabletop_mode_blocks_movement(self):
        movement = parse_spoken_command("come here")
        self.assertFalse(allow_action(movement, "tabletop", False))
        self.assertTrue(allow_action(movement, "floor", False))

    def test_emergency_stop_blocks_new_movement(self):
        movement = parse_spoken_command("go to marker")
        self.assertFalse(allow_action(movement, "floor", True))

    def test_emotion_request_stays_within_allowed_palette(self):
        self.assertEqual(parse_spoken_command("show happy"), CommandDecision("emotion", "happy"))
        self.assertEqual(parse_spoken_command("show terrified").action, "conversation")

    def test_navigation_target_resolves_named_objects_in_scene(self):
        self.assertEqual(explicit_navigation_target("Please drive to the bench."), "scene-bench")
        self.assertEqual(explicit_navigation_target("Approach the potted plant."), "scene-plant")
        self.assertEqual(explicit_navigation_target("Move near the yellow marker."), "target-A")
        self.assertEqual(explicit_navigation_target("Go to the purple target."), "target-B")

    def test_navigation_target_rejects_vague_or_multiple_objects(self):
        self.assertIsNone(explicit_navigation_target("Go to that object."))
        self.assertIsNone(explicit_navigation_target("Go to the bench or plant."))
        self.assertIsNone(explicit_navigation_target("Tell me about the bench."))
        self.assertTrue(is_scene_navigation_request("Go to that object."))
        self.assertTrue(is_scene_navigation_request("Go to the bench or plant."))
        self.assertFalse(is_scene_navigation_request("Tell me about the bench."))

    def test_navigation_target_rejects_negated_or_non_direct_statements(self):
        self.assertIsNone(explicit_navigation_target("Do not go to the bench."))
        self.assertIsNone(explicit_navigation_target("Don't approach the potted plant."))
        self.assertIsNone(explicit_navigation_target("I might go to the bench later."))

    def test_scene_navigation_requires_matching_visible_target_and_floor_mode(self):
        self.assertIsNone(validate_scene_navigation(
            "Please drive to the bench.", "scene-bench", "floor", False,
            {"scene-bench"}, 0.4,
        ))
        self.assertEqual(validate_scene_navigation(
            "Please drive to the bench.", "scene-bench", "floor", False,
            {"scene-plant"}, 0.4,
        ), "target_not_visible")
        self.assertEqual(validate_scene_navigation(
            "Please drive to the bench.", "scene-bench", "tabletop", False,
            {"scene-bench"}, 0.4,
        ), "rejected_tabletop")
        self.assertEqual(validate_scene_navigation(
            "Do not approach the bench.", "scene-bench", "floor", False,
            {"scene-bench"}, 0.4,
        ), "intent_not_explicit")

    def test_scene_navigation_rejects_stale_vision_and_emergency_stop(self):
        args = ("Approach the potted plant.", "scene-plant", "floor", False,
                {"scene-plant"})
        self.assertEqual(validate_scene_navigation(*args, 1.26), "recognition_frame_stale")
        self.assertEqual(
            validate_scene_navigation(args[0], args[1], args[2], True, args[4], 0.1),
            "rejected_emergency_stop",
        )


if __name__ == "__main__":
    unittest.main()
