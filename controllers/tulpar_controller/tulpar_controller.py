"""Development controller for the TULPAR Webots demonstration scene.

Keyboard input is deliberately kept as a development adapter. The command dispatcher
is independent from it so voice, local LLM, and vision adapters can use the same gates.
"""

from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Thread
from tempfile import NamedTemporaryFile
import json
import math
import os
import sys
import time

from controller import Supervisor, Keyboard

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.command_policy import allow_action, parse_spoken_command
from core.diagnostics import format_status_event
from core.dialogue import DialogueError, generate_local_dialogue, generate_local_vision_summary
from core.face_animation import display_oval_from_bounds, eye_pose, mouth_curve_points
from core.microphone import VoskMicrophone
from core.navigation import approach_command
from core.pointing import (
    ImagePoint,
    recognized_world_target,
    select_pointed_target,
    update_selection_success,
)
from core.range_safety import RangeSafetyMonitor
from core.stop_measurement import WheelStopDetector
from core.trial_recorder import TrialRecorder
from core.showcase import Showcase
from core.viewpoint import look_at_orientation


TIME_STEP = 32
APPROACH_DISTANCE = 0.50
MAX_RECOGNITION_AGE = 1.25
MAX_SPEED = 3.0
TURN_SPEED = 1.7
ARRIVAL_TOLERANCE = 0.08
FLOOR_START = [-1.7, -1.1, 0.07]
TABLETOP_START = [-2.45, -1.65, 0.575]


class TulparController:
    def __init__(self):
        self.robot = Supervisor()
        self.keyboard = Keyboard()
        self.keyboard.enable(TIME_STEP)
        self.last_keyboard_key = -1
        self.left_tracks = [
            self.robot.getDevice("left front track motor"),
            self.robot.getDevice("left rear track motor"),
        ]
        self.right_tracks = [
            self.robot.getDevice("right front track motor"),
            self.robot.getDevice("right rear track motor"),
        ]
        self.track_sensors = [
            self.robot.getDevice("left front track sensor"),
            self.robot.getDevice("left rear track sensor"),
            self.robot.getDevice("right front track sensor"),
            self.robot.getDevice("right rear track sensor"),
        ]
        self.left_arm = self.robot.getDevice("left shoulder")
        self.right_arm = self.robot.getDevice("right shoulder")
        self.gps = self.robot.getDevice("gps")
        self.imu = self.robot.getDevice("imu")
        self.range_sensor = self.robot.getDevice("front range sensor")
        self.speaker = self.robot.getDevice("speaker")
        self.face = self.robot.getDevice("face display")
        self.camera = self.robot.getDevice("robot camera")
        self.marker_nodes = {
            "target-A": self.robot.getFromDef("MARKER_A"),
            "target-B": self.robot.getFromDef("MARKER_B"),
        }
        self.operator_node = self.robot.getFromDef("OPERATOR")
        self.pointing_nodes = {
            "operator-shoulder": self.robot.getFromDef("OPERATOR_SHOULDER"),
            "operator-fingertip": self.robot.getFromDef("OPERATOR_FINGERTIP"),
        }
        self.latest_recognition = {}
        self.last_recognition_time = None
        self.last_recognition_refresh = -1.0
        self.last_selected_marker = None
        self.pointing_pose_ready_time = 0.0
        for device in (self.gps, self.imu, self.range_sensor, self.camera):
            device.enable(TIME_STEP)
        self.camera.recognitionEnable(1000)
        for sensor in self.track_sensors:
            sensor.enable(TIME_STEP)
        for motor in (*self.left_tracks, *self.right_tracks):
            motor.setPosition(float("inf"))
            motor.setVelocity(0.0)
        self.mode = "floor"
        self.camera_view = "side"
        self.viewpoint_node = self.robot.getFromDef("SCENE_VIEW")
        if self.viewpoint_node is None:
            raise RuntimeError("world must define the SCENE_VIEW Viewpoint")
        self.viewpoint_position = self.viewpoint_node.getField("position")
        self.viewpoint_orientation = self.viewpoint_node.getField("orientation")
        self.self_node = self.robot.getSelf()
        self.translation_field = self.self_node.getField("translation")
        self.rotation_field = self.self_node.getField("rotation")
        self.emergency_stop = False
        self.action = None
        self.target = None
        self.command_received_at = None
        self.pending_movement_response_start = None
        self.pending_greeting_response_start = None
        self.trial_scenario_success = False
        self.trial_target_selection_correct = None
        self.approach_motion_started = False
        self.last_stop_reason = None
        self.last_stop_had_motion = False
        self.stop_detector = WheelStopDetector()
        self.range_safety = RangeSafetyMonitor()
        self.range_fault_injected = False
        self.range_retry_announced = False
        self.pending_stop_time = None
        self.emotion = "neutral"
        self.last_face_frame_time = -1.0
        self.wave_phase = 0.0
        self.event_file = Path(os.environ.get(
            "TULPAR_EVENT_LOG",
            Path(__file__).resolve().parents[2] / "logs" / "tulpar-events.jsonl",
        ))
        self.capture_dir = Path(os.environ["TULPAR_CAPTURE_DIR"]) if os.environ.get("TULPAR_CAPTURE_DIR") else None
        if self.capture_dir:
            self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.auto_demo = os.environ.get("TULPAR_AUTO_DEMO") == "1" or self.robot.getWorldPath().endswith("tulpar_showcase.wbt")
        if self.auto_demo and self.capture_dir is None:
            self.capture_dir = PROJECT_ROOT / "logs" / "showcase"
            self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.auto_demo_stage = 0
        self.auto_demo_started_at = None
        self.trial_recorder = TrialRecorder(
            Path(__file__).resolve().parents[2] / "logs" / "technical-trial-results.csv"
        )
        self.event_file.parent.mkdir(exist_ok=True)
        self.transcripts = Queue()
        self.voice_errors = Queue()
        self.dialogue_requests = Queue(maxsize=4)
        self.dialogue_results = Queue()
        self.dialogue_worker = Thread(target=self._dialogue_loop, name="tulpar-dialogue", daemon=True)
        self.dialogue_worker.start()
        self.last_vision_sample_time = 0.0
        self.voice_listener = None
        model_path = os.environ.get("TULPAR_VOSK_MODEL")
        if model_path:
            try:
                self.voice_listener = VoskMicrophone(
                    model_path, self.transcripts.put, self.voice_errors.put
                )
                self.voice_listener.start()
                self.log("microphone", "starting", model_path=model_path)
            except Exception as error:
                self.voice_errors.put(str(error))
        else:
            self.log("microphone", "disabled", reason="TULPAR_VOSK_MODEL is not configured")
        self.draw_face("neutral")
        self.set_camera_view("side")
        self.say("TULPAR is ready.")
        self.log("startup", "ready")
        self.showcase = Showcase(self)
        if self.auto_demo:
            self.showcase.start(record=True)

    def _dialogue_loop(self):
        """Keep local LLM latency off the Webots motor-control loop."""
        while True:
            request = self.dialogue_requests.get()
            if request is None:
                return
            transcript, image_bytes = request
            vision_summary = None
            vision_error = None
            if image_bytes:
                try:
                    vision_summary = generate_local_vision_summary(image_bytes, transcript)
                except DialogueError as error:
                    vision_error = str(error)
            try:
                result = generate_local_dialogue(transcript, vision_summary)
                self.dialogue_results.put(("ok", transcript, result, bool(image_bytes), vision_error))
            except DialogueError as error:
                self.dialogue_results.put(("error", transcript, str(error), bool(image_bytes), vision_error))

    def capture_dialogue_frame(self):
        """Capture at most one temporary JPEG frame per second during dialogue."""
        now = time.monotonic()
        if now - self.last_vision_sample_time < 1.0:
            return None
        image_path = None
        try:
            with NamedTemporaryFile(suffix=".jpg", delete=False) as image_file:
                image_path = Path(image_file.name)
            if self.camera.saveImage(str(image_path), 88) != 0:
                self.log("vision", "frame_capture_failed")
                return None
            image = image_path.read_bytes()
            self.last_vision_sample_time = now
            self.log("vision", "frame_captured", bytes=len(image))
            return image
        except Exception as error:
            self.log("vision", "frame_capture_failed", detail=str(error))
            return None
        finally:
            if image_path:
                image_path.unlink(missing_ok=True)

    def process_voice_io(self):
        while True:
            try:
                error = self.voice_errors.get_nowait()
            except Empty:
                break
            self.log("microphone", "error", detail=error)

        while True:
            try:
                transcript = self.transcripts.get_nowait()
            except Empty:
                break
            self.dispatch_spoken_text(transcript)

        while True:
            try:
                status, transcript, result, vision_used, vision_error = self.dialogue_results.get_nowait()
            except Empty:
                break
            if status == "ok":
                self.set_emotion(result.emotion)
                self.say(result.response)
                self.log(
                    "local_dialogue", "spoken", vision_used=vision_used,
                    response_char_count=len(result.response), emotion=result.emotion,
                )
                if vision_error:
                    self.log("vision", "model_error", detail=vision_error)
            else:
                self.set_emotion("neutral")
                self.say("My local conversation model is unavailable right now.")
                self.log("local_dialogue", "error", detail=result, vision_used=vision_used)
                if vision_error:
                    self.log("vision", "model_error", detail=vision_error)

    def log(self, command, outcome, **extra):
        trial = getattr(self, "trial_recorder", None)
        active_trial_id = trial.current.trial_id if trial and trial.current else None
        row = {
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "simulated_time_s": round(self.robot.getTime(), 3),
            "command": command,
            "mode": self.mode,
            "outcome": outcome,
            **({"trial_id": active_trial_id} if active_trial_id else {}),
            **extra,
        }
        with self.event_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")
        print(format_status_event(row), flush=True)

    def set_camera_view(self, view=None):
        """Cycle report-facing side, overview, overhead, and follow views."""
        views = ("side", "overview", "overhead", "robot")
        if view is None:
            view = views[(views.index(self.camera_view) + 1) % len(views)]
        if view not in views:
            raise ValueError(f"unknown camera view: {view}")
        self.camera_view = view
        if view == "side":
            # Side-on to the X-axis route: robot, operator, floor markers, and
            # the separate tabletop setup remain visible in one composition.
            position, target, up = (2.8, -5.2, 3.0), (-0.35, -0.1, 0.55), (0.0, 0.0, 1.0)
            self._apply_viewpoint(position, target, up)
        elif view == "overview":
            position, target, up = (2.9, -4.3, 4.1), (0.0, 0.0, 0.55), (0.0, 0.0, 1.0)
            self._apply_viewpoint(position, target, up)
        elif view == "overhead":
            position, target, up = (0.0, -0.1, 7.0), (0.0, -0.1, 0.0), (0.0, -1.0, 0.0)
            self._apply_viewpoint(position, target, up)
        else:
            self.update_robot_follow_view()
        self.log("viewpoint", "changed", view=view)

    def _apply_viewpoint(self, position, target, up=(0.0, 0.0, 1.0)):
        self.viewpoint_position.setSFVec3f(list(position))
        self.viewpoint_orientation.setSFRotation(
            list(look_at_orientation(position, target, up))
        )

    def update_robot_follow_view(self):
        if self.camera_view != "robot":
            return
        x, y, z = self.gps.getValues()
        yaw = self.imu.getRollPitchYaw()[2]
        local_x, local_y = 1.05, -1.35
        offset_x = math.cos(yaw) * local_x - math.sin(yaw) * local_y
        offset_y = math.sin(yaw) * local_x + math.cos(yaw) * local_y
        position = (x + offset_x, y + offset_y, z + 1.05)
        target = (x, y, z + 0.30)
        self._apply_viewpoint(position, target)

    def say(self, message, utterance_type="response"):
        self.last_utterance = message
        self.speaker.speak(message, 1.0)
        self.log(
            "voice_output", "started", response_char_count=len(message),
            utterance_type=utterance_type,
        )

    def draw_face(self, emotion, time_s=None):
        self.emotion = emotion
        if time_s is None:
            time_s = self.robot.getTime()
        pose = eye_pose(emotion, time_s)
        canvas = self.face
        canvas.setColor(0x071724)
        canvas.fillRectangle(0, 0, 256, 320)
        eye_color = 0x9FF6FF
        mouth_color = 0x66CFE0
        for x, openness in ((54, pose.left_open), (148, pose.right_open)):
            eye_height = max(4, int(62 * openness))
            eye_y = 112 - eye_height // 2
            canvas.setColor(eye_color)
            if openness < 0.14:
                canvas.drawLine(x, 112, x + 54, 112)
            else:
                canvas.fillOval(*display_oval_from_bounds(x, eye_y, 54, eye_height))
                pupil_x = x + 21 + int(8 * pose.pupil_x)
                pupil_y = 112 + int(14 * pose.pupil_y)
                pupil_size = max(7, min(15, int(14 * openness)))
                canvas.setColor(0x06202C)
                canvas.fillOval(*display_oval_from_bounds(
                    pupil_x - pupil_size // 2,
                    pupil_y - pupil_size // 2,
                    pupil_size,
                    pupil_size,
                ))
        canvas.setColor(eye_color)
        if emotion == "angry":
            canvas.drawLine(46, 76, 108, 96)
            canvas.drawLine(210, 76, 148, 96)
        canvas.setColor(mouth_color)
        if emotion in ("happy", "love", "wink"):
            points = mouth_curve_points(emotion)
            for start, end in zip(points, points[1:]):

                for dy in range(-2, 3):
                    canvas.drawLine(start[0], start[1]+dy, end[0], end[1]+dy)
        elif emotion == "sad":
            points = mouth_curve_points(emotion)
            for start, end in zip(points, points[1:]):

                for dy in range(-2, 3):
                    canvas.drawLine(start[0], start[1]+dy, end[0], end[1]+dy)
        elif emotion == "surprised":
            mouth_height = 48 + int(6 * math.sin(time_s * 2.4))
            canvas.drawOval(*display_oval_from_bounds(109, 181, 38, mouth_height))
        elif emotion == "thinking":
            canvas.fillRectangle(96, 206, 64, 7)
        else:
            canvas.fillRectangle(96, 205, 64, 7)
        canvas.setColor(0xD9F8FA)
        canvas.drawText(emotion.upper(), 12, 292)
        self.last_face_frame_time = time_s

    def update_face_animation(self):
        now = self.robot.getTime()
        if now - self.last_face_frame_time >= 0.12:
            self.draw_face(self.emotion, now)

    def capture_scene(self, name):
        """Export the rendered 3D viewport for visual QA and scripted demos."""
        if self.capture_dir:
            path = self.capture_dir / f"{name}.png"
            self.robot.exportImage(str(path), 95)
            camera_path = self.capture_dir / f"{name}_robot_camera.png"
            camera_ok = self.camera.saveImage(str(camera_path), 95)
            self.log(
                "scene_capture", "exported", file=str(path),
                robot_camera_file=str(camera_path) if camera_ok == 0 else None,
            )

    def tracks(self, left, right):
        if self.mode != "floor" or self.emergency_stop:
            left = right = 0.0
        for motor in self.left_tracks:
            motor.setVelocity(left)
        for motor in self.right_tracks:
            motor.setVelocity(right)

    def stop(self, reason="command"):
        self.last_stop_had_motion = self.approach_motion_started
        self.last_stop_reason = reason
        self.tracks(0.0, 0.0)
        self.action = None
        self.target = None
        self.pending_stop_time = (
            self.command_received_at
            if self.command_received_at is not None else self.robot.getTime()
        )
        self.pending_movement_response_start = None
        self.pending_greeting_response_start = None
        self.approach_motion_started = False
        self.stop_detector.stable_count = 0
        self.log("stop", "commanded", reason=reason)
        self.draw_face("surprised")
        self.log("face_display", "emotion_started", emotion="surprised")
        self.say("Stopped.")

    def update_stop_measurement(self):
        now = self.robot.getTime()
        sample = self.stop_detector.update(
            tuple(sensor.getValue() for sensor in self.track_sensors), now
        )
        if self.pending_stop_time is not None and sample.stopped:
            self.log(
                "stop",
                "confirmed",
                stopping_time_s=round(now - self.pending_stop_time, 3),
                max_wheel_speed_rad_s=round(max(abs(speed) for speed in sample.wheel_speeds), 4),
                reason=self.last_stop_reason,
            )
            self.pending_stop_time = None
            trial = self.trial_recorder.current
            if (
                trial and trial.scenario == "stop"
                and self.last_stop_reason == "command" and self.last_stop_had_motion
            ):
                self.trial_scenario_success = True

    def set_emotion(self, emotion):
        self.draw_face(emotion)
        poses = {
            "neutral": (0.0, 0.0), "happy": (-0.25, 0.25), "sad": (0.25, -0.25),
            "surprised": (-0.45, 0.45), "angry": (0.15, -0.15), "sleepy": (0.2, -0.2),
            "wink": (-0.35, 0.35), "love": (-0.30, 0.30), "thinking": (0.08, -0.08),
        }
        left, right = poses[emotion]
        self.left_arm.setPosition(left)
        self.right_arm.setPosition(right)
        self.log("face_display", "emotion_started", emotion=emotion)
        self.log("arm_pose", "emotion_started", emotion=emotion)

    def begin_approach(self, target, label):
        if self.mode != "floor":
            self.say("Movement is disabled in tabletop mode.")
            self.log(label, "rejected_tabletop")
            return
        if self.emergency_stop:
            self.say("Emergency stop is active.")
            self.log(label, "rejected_emergency_stop")
            return
        self.target = target
        self.action = "approach"
        self.approach_motion_started = False
        self.pending_movement_response_start = (
            self.command_received_at
            if self.command_received_at is not None else self.robot.getTime()
        )
        self.log(label, "accepted", target=target)
        self.set_emotion("thinking")
        response = "Coming to you." if label == "come_to_me" else "Moving to the marked target."
        self.say(response)

    def refresh_recognition(self):
        """Snapshot camera recognitions at the configured one-second cadence."""
        now = self.robot.getTime()
        if now - self.last_recognition_refresh < 1.0:
            return
        self.last_recognition_refresh = now
        self.latest_recognition = {}
        for item in self.camera.getRecognitionObjects():
            label = item.getModel()
            if label:
                x, y = item.getPositionOnImage()
                self.latest_recognition[label] = (float(x), float(y))
        self.last_recognition_time = now

    def detected_operator_target(self):
        """Use camera visibility as a gate before reading the simulated pose."""
        now = self.robot.getTime()
        if (
            self.last_recognition_time is None
            or now - self.last_recognition_time > MAX_RECOGNITION_AGE
        ):
            self.log("come_to_me", "rejected_vision", reason="recognition_frame_stale")
            self.say("I need a fresh camera image. Please repeat the command.")
            return None
        target = recognized_world_target(
            self.latest_recognition,
            "operator-torso",
            self.operator_node.getPosition(),
        )
        if target is None:
            self.log("come_to_me", "rejected_vision", reason="operator_not_visible")
            self.say("I cannot see you. Please move into view and repeat the command.")
            return None
        image_x, image_y = self.latest_recognition["operator-torso"]
        self.log(
            "come_to_me", "vision_target_selected", target="operator",
            image_x=round(image_x, 1), image_y=round(image_y, 1),
        )
        return target

    def pointed_marker_target(self):
        self.last_selected_marker = None
        if self.robot.getTime() < self.pointing_pose_ready_time:
            self.log("go_to_marker", "rejected_vision", reason="waiting_for_next_camera_frame")
            self.say("Please hold your pointing pose while I check the camera.")
            return None
        shoulder = self.latest_recognition.get("operator-shoulder")
        fingertip = self.latest_recognition.get("operator-fingertip")
        markers = [
            ImagePoint(label, *self.latest_recognition[label])
            for label in self.marker_nodes
            if label in self.latest_recognition
        ]
        result = select_pointed_target(shoulder, fingertip, markers)
        if result.target is None:
            self.log("go_to_marker", "rejected_vision", reason=result.reason)
            trial = self.trial_recorder.current
            if trial and trial.scenario == "approach_marked_target":
                self.log(
                    "target_selection", "rejected", expected=trial.target,
                    reason=result.reason,
                )
            self.say("I cannot identify the pointed marker. Please point again.")
            return None
        self.last_selected_marker = result.target
        marker_position = self.marker_nodes[result.target].getPosition()
        target_xy = (float(marker_position[0]), float(marker_position[1]))
        self.log(
            "go_to_marker", "vision_target_selected", target=result.target,
            pointing_error_deg=round(result.angular_error_deg or 0.0, 2),
        )
        return target_xy

    def set_simulated_pointing_target(self, target_label):
        """Reposition the virtual fingertip to create a repeatable pointing pose."""
        marker = self.marker_nodes[target_label].getPosition()
        shoulder = self.pointing_nodes["operator-shoulder"].getPosition()
        dx, dy = marker[0] - shoulder[0], marker[1] - shoulder[1]
        # The visible pole extends above its floor marker; aim at its centre.
        dz = marker[2] + 0.28 - shoulder[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length <= 0.0:
            return
        extension = 0.55
        fingertip = self.pointing_nodes["operator-fingertip"]
        fingertip.getField("translation").setSFVec3f([
            shoulder[0] + dx / length * extension,
            shoulder[1] + dy / length * extension,
            shoulder[2] + dz / length * extension,
        ])
        self.pointing_pose_ready_time = self.robot.getTime() + 1.0
        self.log("simulated_pointing_pose", "set", target=target_label)

    def update_approach(self):
        range_m = float("nan") if self.range_fault_injected else float(self.range_sensor.getValue())
        range_decision = self.range_safety.evaluate(
            range_m, max_range_m=1.5, stop_distance_m=0.50
        )
        if range_decision.status == "retry":
            self.tracks(0.0, 0.0)
            if not self.range_retry_announced:
                self.say("The front sensor gave an invalid reading. Checking once more.")
                self.log("range_sensor", "retry", reason="invalid_reading")
                self.range_retry_announced = True
            return
        if range_decision.status == "sensor_fault":
            self.log("range_sensor", "stopped", reason="two_invalid_readings")
            self.range_retry_announced = False
            self.stop("range_sensor_failed")
            return
        if range_decision.status == "obstacle":
            x, y, _ = self.gps.getValues()
            centre_distance = math.hypot(self.target[0] - x, self.target[1] - y)
            yaw = self.imu.getRollPitchYaw()[2]
            target_yaw = math.atan2(self.target[1] - y, self.target[0] - x)
            heading_error = abs(math.atan2(math.sin(target_yaw-yaw), math.cos(target_yaw-yaw)))
            self.range_retry_announced = False
            if centre_distance <= 1.0 and heading_error < 0.20:
                self.complete_approach(range_decision.distance_m, "front_sensor_to_surface")
            else:
                self.log("range_sensor", "stopped", reason="unexpected_front_return", distance_m=round(range_decision.distance_m, 3))
                self.stop("unexpected_front_return")
            return
        if self.range_retry_announced:
            self.log("range_sensor", "retry_recovered")
            self.range_retry_announced = False

        x, y, _ = self.gps.getValues()
        yaw = self.imu.getRollPitchYaw()[2]
        command = approach_command(
            (x, y), yaw, self.target,
            stop_distance=APPROACH_DISTANCE,
            arrival_tolerance=ARRIVAL_TOLERANCE,
            max_speed=MAX_SPEED,
            turn_speed=TURN_SPEED,
        )
        if command.arrived:
            self.complete_approach(command.distance, "simulator_centre_distance")
            return
        self.tracks(command.left, command.right)
        if command.left or command.right:
            self.approach_motion_started = True
        if self.pending_movement_response_start is not None and (command.left or command.right):
            self.log(
                "movement", "started",
                response_time_s=round(self.robot.getTime() - self.pending_movement_response_start, 3),
            )
            self.pending_movement_response_start = None

    def complete_approach(self, distance, measurement):
        self.tracks(0.0, 0.0)
        self.action = None
        self.target = None
        self.pending_movement_response_start = None
        self.approach_motion_started = False
        trial = self.trial_recorder.current
        if trial and trial.scenario == "approach_operator":
            self.trial_scenario_success = True
        elif trial and trial.scenario == "approach_marked_target":
            self.trial_scenario_success = self.trial_target_selection_correct is True
        self.set_emotion("happy")
        self.say("I have arrived.")
        self.log("approach", "arrived", distance=round(distance, 3), measurement=measurement)

    def update_wave(self):
        self.tracks(0.0, 0.0)
        self.wave_phase += TIME_STEP / 1000.0
        swing = 0.42 * math.sin(self.wave_phase * 7.0)
        self.left_arm.setPosition(-0.28 + swing)
        self.right_arm.setPosition(0.20)
        if self.pending_greeting_response_start is not None:
            self.log(
                "greeting", "gesture_started",
                response_time_s=round(self.robot.getTime() - self.pending_greeting_response_start, 3),
            )
            self.pending_greeting_response_start = None
        if self.wave_phase > 2.2:
            self.wave_phase = 0.0
            self.action = None
            trial = self.trial_recorder.current
            if trial and trial.scenario == "greeting":
                self.trial_scenario_success = True
            self.set_emotion("happy")
            self.log("greeting", "completed")

    def command(self, value):
        if value == "operator":
            target = self.detected_operator_target()
            if target is not None:
                self.begin_approach(target, "come_to_me")
        elif value == "marker":
            target = self.pointed_marker_target()
            if target is not None:
                trial = self.trial_recorder.current
                if trial and trial.scenario == "approach_marked_target":
                    correct = self.last_selected_marker == trial.target
                    self.trial_target_selection_correct = update_selection_success(
                        self.trial_target_selection_correct,
                        trial.target,
                        self.last_selected_marker,
                    )
                    self.log(
                        "target_selection", "correct" if correct else "incorrect",
                        expected=trial.target, selected=self.last_selected_marker,
                    )
                self.begin_approach(target, "go_to_marker")
        elif value == "stop":
            self.stop()
        elif value == "greet":
            self.tracks(0.0, 0.0)
            self.action = "wave"
            self.wave_phase = 0.0
            self.pending_greeting_response_start = (
                self.command_received_at
                if self.command_received_at is not None else self.robot.getTime()
            )
            self.log("greeting", "accepted")
            self.set_emotion("happy")
            self.say("Hello.")
        elif value == "mode":
            if self.trial_recorder.current is not None:
                self.say("Finish the active trial before changing mode.")
                self.log("mode", "change_rejected_active_trial")
                return
            self.stop("mode_change")
            if self.mode == "floor":
                self.translation_field.setSFVec3f(TABLETOP_START)
                self.mode = "tabletop"
            else:
                self.translation_field.setSFVec3f(FLOOR_START)
                self.mode = "floor"
            self.rotation_field.setSFRotation([0.0, 0.0, 1.0, 0.0])
            self.self_node.resetPhysics()
            self.say(f"{self.mode} mode selected.")
            self.log("mode", "changed")
        elif value == "emergency":
            self.emergency_stop = not self.emergency_stop
            self.stop("emergency_stop")
            self.draw_face("angry" if self.emergency_stop else "neutral")
            self.say("Emergency stop active." if self.emergency_stop else "Emergency stop cleared.")
            self.log("emergency_stop", "active" if self.emergency_stop else "cleared")
        elif value == "range_fault":
            self.range_fault_injected = not self.range_fault_injected
            self.log("range_sensor_fault_injection", "enabled" if self.range_fault_injected else "disabled")
        else:
            self.set_emotion(value)

    def start_trial(self):
        if self.trial_recorder.current is not None:
            self.say("A trial is already active.")
            self.log("trial", "start_rejected_active_trial")
            return
        trial = self.trial_recorder.next_trial()
        if trial is None:
            self.say("All planned trials already have recorded outcomes.")
            self.log("trial", "plan_complete")
            return
        if trial.placement != self.mode:
            self.say(f"Trial {trial.trial_id} requires {trial.placement} mode.")
            self.log(
                "trial", "start_rejected_wrong_mode", trial_id=trial.trial_id,
                required_mode=trial.placement,
            )
            return
        if self.emergency_stop or self.range_fault_injected:
            self.say("Clear the emergency stop and sensor fault before a trial.")
            self.log("trial", "start_rejected_safety_state", trial_id=trial.trial_id)
            return

        self.tracks(0.0, 0.0)
        self.action = None
        self.target = None
        self.approach_motion_started = False
        self.translation_field.setSFVec3f(FLOOR_START if self.mode == "floor" else TABLETOP_START)
        self.rotation_field.setSFRotation([0.0, 0.0, 1.0, 0.0])
        self.self_node.resetPhysics()
        self.left_arm.setPosition(0.0)
        self.right_arm.setPosition(0.0)
        self.draw_face("neutral")
        self.stop_detector.stable_count = 0
        self.range_safety = RangeSafetyMonitor()
        self.pending_stop_time = None
        self.pending_movement_response_start = None
        self.pending_greeting_response_start = None
        self.trial_scenario_success = False
        self.trial_target_selection_correct = None
        trial = self.trial_recorder.start_next(self.robot.getTime())

        instruction = f"Run: {trial.command}."
        if trial.scenario == "stop":
            self.action = "approach"
            self.target = (1.45, -1.10)
            self.approach_motion_started = False
            self.set_emotion("thinking")
            instruction = "I am moving toward the operator. Say stop while the tracks are moving."
        if trial.scenario == "approach_marked_target":
            control_key = "3" if trial.target == "target-A" else "4"
            instruction = (
                f"Set the virtual pointing pose to {trial.target} with key {control_key}, "
                f"then say: {trial.command}."
            )
        self.say(f"Trial {trial.trial_id} started. {instruction}", utterance_type="trial_prompt")
        self.log(
            "trial", "started", trial_id=trial.trial_id, scenario=trial.scenario,
            placement=trial.placement,
        )

    def finish_trial(self, outcome):
        trial = self.trial_recorder.current
        if outcome == "pass" and trial and not self.trial_scenario_success:
            self.say("The required behaviour has not completed yet; record fail or continue the trial.")
            self.log("trial", "pass_rejected_incomplete", trial_id=trial.trial_id)
            return
        if outcome == "fail" and trial:
            # A failed attempt must not leave the simulated robot moving after
            # its result has been recorded. Do not call stop(): that path
            # represents the measured operator stop command in stop trials.
            self.tracks(0.0, 0.0)
            self.action = None
            self.target = None
            self.approach_motion_started = False
            self.pending_movement_response_start = None
            self.pending_greeting_response_start = None
            self.pending_stop_time = None
            self.wave_phase = 0.0
            self.left_arm.setPosition(0.0)
            self.right_arm.setPosition(0.0)
            self.draw_face("neutral")
            self.log("trial", "failed_behaviour_cancelled", trial_id=trial.trial_id)
        try:
            row = self.trial_recorder.finish(outcome, self.robot.getTime())
        except RuntimeError:
            self.say("Start a trial before recording its result.")
            self.log("trial", "result_rejected_no_active_trial", requested_outcome=outcome)
            return
        self.say(
            f"Trial {row['trial_id']} recorded as {outcome}.",
            utterance_type="trial_result",
        )
        self.log(
            "trial", "result_recorded", trial_id=row["trial_id"], outcome=outcome,
            duration_s=float(row["duration_s"]),
        )

    def dispatch_spoken_text(self, text):
        """Route ASR text through the fixed action policy before any actuation.

        Movement is dispatched directly from the allow-listed transcript. Only
        ordinary conversation is sent to the local LLM, which cannot issue actions.
        """
        decision = parse_spoken_command(text)
        if not allow_action(decision, self.mode, self.emergency_stop):
            self.log("spoken_text", "rejected_by_safety_gate", action=decision.action)
            self.say("That action is unavailable in the current mode.")
            return
        handlers = {
            "stop": lambda: self.command("stop"),
            "approach_operator": lambda: self.command("operator"),
            "approach_marker": lambda: self.command("marker"),
            "greet": lambda: self.command("greet"),
            "emotion": lambda: self.command(decision.emotion),
        }
        handler = handlers.get(decision.action)
        if handler:
            self.command_received_at = self.robot.getTime()
            try:
                handler()
            finally:
                self.command_received_at = None
            return
        self.log("spoken_text", "conversation_needed")
        self.set_emotion("thinking")
        try:
            self.dialogue_requests.put_nowait((text, self.capture_dialogue_frame()))
        except Full:
            self.say("Please wait while I finish my last answer.")
            self.log("local_dialogue", "queue_full")

    def keyboard_command(self, key):
        mapping = {
            ord("1"): "operator", ord("2"): "marker", ord("S"): "stop", ord("G"): "greet",
            ord("T"): "mode", ord("E"): "emergency", ord("H"): "happy", ord("A"): "angry",
            ord("D"): "sad", ord("P"): "surprised", ord("Y"): "sleepy", ord("W"): "wink",
            ord("O"): "love", ord("I"): "thinking", ord("N"): "neutral",
            ord("F"): "range_fault",
        }
        command = mapping.get(key)
        if command:
            self.command_received_at = self.robot.getTime()
            try:
                self.command(command)
            finally:
                self.command_received_at = None
        elif key == ord("5"):
            self.start_trial()
        elif key == ord("6"):
            self.finish_trial("pass")
        elif key == ord("7"):
            self.finish_trial("fail")
        elif key == ord("3"):
            self.set_simulated_pointing_target("target-A")
        elif key == ord("4"):
            self.set_simulated_pointing_target("target-B")
        elif key == ord("R"):
            self.showcase.start(record=True)
        elif key == ord("B"):
            self.showcase.start()
        elif key == ord("C"):
            self.set_camera_view()

    def run(self):
        try:
            while self.robot.step(TIME_STEP) != -1:
                self.update_robot_follow_view()
                self.update_face_animation()
                self.refresh_recognition()
                self.update_stop_measurement()
                self.process_voice_io()
                self.showcase.update()
                self.showcase.overlay()
                key = self.keyboard.getKey()
                if key != -1 and key != self.last_keyboard_key:
                    self.keyboard_command(key)
                self.last_keyboard_key = key
                if self.action == "approach":
                    self.update_approach()
                elif self.action == "wave":
                    self.update_wave()
        finally:
            if self.voice_listener:
                self.voice_listener.stop()
            try:
                self.dialogue_requests.put_nowait(None)
            except Full:
                pass


if __name__ == "__main__":
    TulparController().run()
