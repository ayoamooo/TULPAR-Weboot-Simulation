import unittest

from core.command_policy import CommandDecision, allow_action, parse_spoken_command


class CommandPolicyTests(unittest.TestCase):
    def test_only_report_commands_start_floor_motion(self):
        self.assertEqual(parse_spoken_command("come to me").action, "approach_operator")
        self.assertEqual(parse_spoken_command("go to that marker").action, "approach_marker")
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


if __name__ == "__main__":
    unittest.main()
