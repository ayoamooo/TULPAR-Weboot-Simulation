import unittest

from core.diagnostics import format_status_event


class DiagnosticsTests(unittest.TestCase):
    def test_formats_decision_details_for_the_webots_console(self):
        line = format_status_event({
            "simulated_time_s": 3.25,
            "mode": "floor",
            "command": "go_to_marker",
            "outcome": "rejected_vision",
            "trial_id": "T11",
            "scenario": "approach_marked_target",
            "expected": "target-A",
            "reason": "ambiguous_pointing",
            "transcript": "private spoken words",
            "response": "private model reply",
        })
        self.assertIn("[TULPAR   3.25s | floor] go_to_marker: rejected_vision", line)
        self.assertIn("trial_id=T11", line)
        self.assertIn("expected=target-A", line)
        self.assertIn("reason=ambiguous_pointing", line)
        self.assertNotIn("private spoken words", line)
        self.assertNotIn("private model reply", line)

    def test_flattens_diagnostic_text_to_one_line(self):
        line = format_status_event({
            "command": "range_sensor",
            "outcome": "stopped",
            "reason": "near\nobstacle",
        })
        self.assertEqual(line.count("\n"), 0)
        self.assertIn("reason=near obstacle", line)


if __name__ == "__main__":
    unittest.main()
