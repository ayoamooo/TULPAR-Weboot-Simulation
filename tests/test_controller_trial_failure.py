import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_PATH = ROOT / "controllers" / "tulpar_controller" / "tulpar_controller.py"


def load_controller_class():
    webots_api = types.ModuleType("controller")
    webots_api.Supervisor = object
    webots_api.Keyboard = object
    module_name = "_tulpar_controller_failure_test"
    spec = importlib.util.spec_from_file_location(module_name, CONTROLLER_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"controller": webots_api}):
        spec.loader.exec_module(module)
    return module.TulparController


TulparController = load_controller_class()


class FakeMotor:
    def __init__(self):
        self.positions = []

    def setPosition(self, position):
        self.positions.append(position)


class FakeRecorder:
    current = types.SimpleNamespace(trial_id="T01")

    def finish(self, outcome, time_s):
        self.current = None
        return {
            "trial_id": "T01",
            "duration_s": "2.000",
        }


class ControllerTrialFailureTests(unittest.TestCase):
    def test_approach_starts_with_a_spoken_response_and_face_state(self):
        controller = TulparController.__new__(TulparController)
        controller.mode = "floor"
        controller.emergency_stop = False
        controller.range_fault_injected = False
        controller.range_retry_announced = False
        controller.range_sensor = types.SimpleNamespace(getValue=lambda: 1.0)
        controller.range_safety = types.SimpleNamespace(
            evaluate=lambda *args, **kwargs: types.SimpleNamespace(status="clear")
        )
        controller.command_received_at = 1.0
        controller.robot = types.SimpleNamespace(getTime=lambda: 1.1)
        controller.events = []
        controller.emotions = []
        controller.spoken = []
        controller.log = lambda *args, **kwargs: controller.events.append(args)
        controller.set_emotion = controller.emotions.append
        controller.say = lambda message, **kwargs: controller.spoken.append(message)

        controller.begin_approach((1.0, 2.0), "come_to_me")

        self.assertEqual(controller.action, "approach")
        self.assertEqual(controller.emotions, ["thinking"])
        self.assertEqual(controller.spoken, ["Coming to you."])

    def test_stop_coordinates_face_voice_and_drive_stop(self):
        controller = TulparController.__new__(TulparController)
        controller.approach_motion_started = True
        controller.command_received_at = 2.0
        controller.robot = types.SimpleNamespace(getTime=lambda: 2.1)
        controller.stop_detector = types.SimpleNamespace(stable_count=2)
        controller.track_commands = []
        controller.events = []
        controller.faces = []
        controller.spoken = []
        controller.tracks = lambda left, right: controller.track_commands.append((left, right))
        controller.log = lambda *args, **kwargs: controller.events.append(args)
        controller.draw_face = controller.faces.append
        controller.say = controller.spoken.append

        controller.stop()

        self.assertEqual(controller.track_commands, [(0.0, 0.0)])
        self.assertEqual(controller.faces, ["surprised"])
        self.assertEqual(controller.spoken, ["Stopped."])
        self.assertIn(("stop", "commanded"), controller.events)
        self.assertIn(("face_display", "emotion_started"), controller.events)

    def test_fail_cancels_motion_and_wave_before_recording_result(self):
        controller = TulparController.__new__(TulparController)
        controller.trial_recorder = FakeRecorder()
        controller.trial_scenario_success = False
        controller.robot = types.SimpleNamespace(getTime=lambda: 3.0)
        controller.left_arm = FakeMotor()
        controller.right_arm = FakeMotor()
        controller.action = "approach"
        controller.target = (1.0, 2.0)
        controller.approach_motion_started = True
        controller.pending_movement_response_start = 1.0
        controller.pending_greeting_response_start = 1.0
        controller.pending_stop_time = 1.5
        controller.wave_phase = 0.8
        controller.track_commands = []
        controller.events = []
        controller.faces = []
        controller.tracks = lambda left, right: controller.track_commands.append((left, right))
        controller.draw_face = lambda emotion: controller.faces.append(emotion)
        controller.say = lambda *args, **kwargs: None
        controller.log = lambda *args, **kwargs: controller.events.append(args)

        controller.finish_trial("fail")

        self.assertEqual(controller.track_commands, [(0.0, 0.0)])
        self.assertIsNone(controller.action)
        self.assertIsNone(controller.target)
        self.assertFalse(controller.approach_motion_started)
        self.assertIsNone(controller.pending_movement_response_start)
        self.assertIsNone(controller.pending_greeting_response_start)
        self.assertIsNone(controller.pending_stop_time)
        self.assertEqual(controller.wave_phase, 0.0)
        self.assertEqual(controller.left_arm.positions, [0.0])
        self.assertEqual(controller.right_arm.positions, [0.0])
        self.assertEqual(controller.faces, ["neutral"])
        self.assertIn(("trial", "failed_behaviour_cancelled"), controller.events)
        self.assertIn(("trial", "result_recorded"), controller.events)


if __name__ == "__main__":
    unittest.main()
