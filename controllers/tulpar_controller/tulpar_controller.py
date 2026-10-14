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
from core.dialogue import DialogueError, generate_local_dialogue, generate_local_vision_summary
from core.face_animation import eye_pose
from core.microphone import VoskMicrophone
from core.navigation import approach_command
from core.pointing import ImagePoint, select_pointed_target
from core.stop_measurement import WheelStopDetector


TIME_STEP = 32
APPROACH_DISTANCE = 0.50
MAX_SPEED = 3.0
TURN_SPEED = 1.7
ARRIVAL_TOLERANCE = 0.08


class TulparController:
    def __init__(self):
        self.robot = Supervisor()
        self.keyboard = Keyboard()
        self.keyboard.enable(TIME_STEP)
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
        self.pointing_nodes = {
            "operator-shoulder": self.robot.getFromDef("OPERATOR_SHOULDER"),
            "operator-fingertip": self.robot.getFromDef("OPERATOR_FINGERTIP"),
        }
        self.latest_recognition = {}
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
        self.self_node = self.robot.getSelf()
        self.translation_field = self.self_node.getField("translation")
        self.emergency_stop = False
        self.action = None
        self.target = None
        self.stop_detector = WheelStopDetector()
        self.pending_stop_time = None
        self.emotion = "neutral"
        self.last_face_frame_time = -1.0
        self.wave_phase = 0.0
        self.event_file = Path(__file__).resolve().parents[2] / "logs" / "tulpar-events.jsonl"
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
        self.say("TULPAR is ready.")
        self.log("startup", "ready")

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
            if not self.camera.saveImage(str(image_path), 88):
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
        row = {
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "simulated_time_s": round(self.robot.getTime(), 3),
            "command": command,
            "mode": self.mode,
            "outcome": outcome,
            **extra,
        }
        with self.event_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")

    def say(self, message):
        self.speaker.speak(message, 1.0)

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
                canvas.fillOval(x, eye_y, 54, eye_height)
                pupil_x = x + 21 + int(8 * pose.pupil_x)
                pupil_y = 112 + int(14 * pose.pupil_y)
                pupil_size = max(7, min(15, int(14 * openness)))
                canvas.setColor(0x06202C)
                canvas.fillOval(pupil_x, pupil_y - pupil_size // 2, pupil_size, pupil_size)
        canvas.setColor(eye_color)
        if emotion == "angry":
            canvas.drawLine(46, 76, 108, 96)
            canvas.drawLine(210, 76, 148, 96)
        canvas.setColor(mouth_color)
        if emotion in ("happy", "love", "wink"):
            canvas.drawArc(78, 175, 100, 58, 10, 160)
        elif emotion == "sad":
            canvas.drawArc(78, 204, 100, 58, 190, 160)
        elif emotion == "surprised":
            mouth_height = 48 + int(6 * math.sin(time_s * 2.4))
            canvas.drawOval(109, 181, 38, mouth_height)
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

    def tracks(self, left, right):
        if self.mode != "floor" or self.emergency_stop:
            left = right = 0.0
        for motor in self.left_tracks:
            motor.setVelocity(left)
        for motor in self.right_tracks:
            motor.setVelocity(right)

    def stop(self, reason="command"):
        self.tracks(0.0, 0.0)
        self.action = None
        self.target = None
        self.pending_stop_time = self.robot.getTime()
        self.stop_detector.stable_count = 0
        self.log("stop", "commanded", reason=reason)
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
            )
            self.pending_stop_time = None

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
        self.log("emotion", "displayed", emotion=emotion)

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
        self.set_emotion("thinking")
        self.say("I am coming.")
        self.log(label, "accepted", target=target)

    def refresh_recognition(self):
        """Snapshot recognized model labels and image centres from the camera."""
        self.latest_recognition = {}
        for item in self.camera.getRecognitionObjects():
            label = item.getModel()
            if label:
                x, y = item.getPositionOnImage()
                self.latest_recognition[label] = (float(x), float(y))

    def pointed_marker_target(self):
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
            self.say("I cannot identify the pointed marker. Please point again.")
            return None
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
        length = math.hypot(dx, dy)
        if length <= 0.0:
            return
        extension = 0.55
        fingertip = self.pointing_nodes["operator-fingertip"]
        fingertip.getField("translation").setSFVec3f([
            shoulder[0] + dx / length * extension,
            shoulder[1] + dy / length * extension,
            shoulder[2] + (marker[2] + 0.28 - shoulder[2]) * extension / length,
        ])
        self.pointing_pose_ready_time = self.robot.getTime() + 1.0
        self.log("simulated_pointing_pose", "set", target=target_label)

    def update_approach(self):
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
            self.tracks(0.0, 0.0)
            self.action = None
            self.target = None
            self.set_emotion("happy")
            self.say("I have arrived.")
            self.log("approach", "arrived", distance=round(command.distance, 3))
            return
        self.tracks(command.left, command.right)

    def update_wave(self):
        self.tracks(0.0, 0.0)
        self.wave_phase += TIME_STEP / 1000.0
        swing = 0.42 * math.sin(self.wave_phase * 7.0)
        self.left_arm.setPosition(-0.28 + swing)
        self.right_arm.setPosition(0.20)
        if self.wave_phase > 2.2:
            self.wave_phase = 0.0
            self.action = None
            self.set_emotion("happy")
            self.say("Hello.")
            self.log("greeting", "completed")

    def command(self, value):
        if value == "operator":
            self.begin_approach((1.45, -1.10), "come_to_me")
        elif value == "marker":
            target = self.pointed_marker_target()
            if target is not None:
                self.begin_approach(target, "go_to_marker")
        elif value == "stop":
            self.stop()
        elif value == "greet":
            self.tracks(0.0, 0.0)
            self.action = "wave"
            self.wave_phase = 0.0
            self.set_emotion("happy")
            self.log("greeting", "accepted")
        elif value == "mode":
            self.stop("mode_change")
            if self.mode == "floor":
                self.translation_field.setSFVec3f([-2.45, -1.65, 0.575])
                self.mode = "tabletop"
            else:
                self.translation_field.setSFVec3f([-1.7, -1.1, 0.07])
                self.mode = "floor"
            self.self_node.resetPhysics()
            self.say(f"{self.mode} mode selected.")
            self.log("mode", "changed")
        elif value == "emergency":
            self.emergency_stop = not self.emergency_stop
            self.stop("emergency_stop")
            self.draw_face("angry" if self.emergency_stop else "neutral")
            self.say("Emergency stop active." if self.emergency_stop else "Emergency stop cleared.")
            self.log("emergency_stop", "active" if self.emergency_stop else "cleared")
        else:
            self.set_emotion(value)

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
            handler()
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
        }
        command = mapping.get(key)
        if command:
            self.command(command)
        elif key == ord("3"):
            self.set_simulated_pointing_target("target-A")
        elif key == ord("4"):
            self.set_simulated_pointing_target("target-B")

    def run(self):
        try:
            while self.robot.step(TIME_STEP) != -1:
                self.update_face_animation()
                self.refresh_recognition()
                self.update_stop_measurement()
                self.process_voice_io()
                key = self.keyboard.getKey()
                if key != -1:
                    self.keyboard_command(key)
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
