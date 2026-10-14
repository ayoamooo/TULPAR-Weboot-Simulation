"""Development controller for the TULPAR Webots demonstration scene.

Keyboard input is deliberately kept as a development adapter. The command dispatcher
is independent from it so voice, local LLM, and vision adapters can use the same gates.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import math
import sys

from controller import Robot, Keyboard

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.command_policy import allow_action, parse_spoken_command


TIME_STEP = 32
APPROACH_DISTANCE = 0.50
MAX_SPEED = 3.0
TURN_SPEED = 1.7
ARRIVAL_TOLERANCE = 0.08


class TulparController:
    def __init__(self):
        self.robot = Robot()
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
        self.left_arm = self.robot.getDevice("left shoulder")
        self.right_arm = self.robot.getDevice("right shoulder")
        self.gps = self.robot.getDevice("gps")
        self.imu = self.robot.getDevice("imu")
        self.range_sensor = self.robot.getDevice("front range sensor")
        self.speaker = self.robot.getDevice("speaker")
        self.face = self.robot.getDevice("face display")
        self.camera = self.robot.getDevice("robot camera")
        for device in (self.gps, self.imu, self.range_sensor, self.camera):
            device.enable(TIME_STEP)
        for motor in (*self.left_tracks, *self.right_tracks):
            motor.setPosition(float("inf"))
            motor.setVelocity(0.0)
        self.mode = "floor"
        self.emergency_stop = False
        self.action = None
        self.target = None
        self.emotion = "neutral"
        self.wave_phase = 0.0
        self.event_file = Path(__file__).resolve().parents[2] / "logs" / "tulpar-events.jsonl"
        self.event_file.parent.mkdir(exist_ok=True)
        self.draw_face("neutral")
        self.say("TULPAR is ready.")
        self.log("startup", "ready")

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

    def draw_face(self, emotion):
        self.emotion = emotion
        canvas = self.face
        canvas.setColor(0x071724)
        canvas.fillRectangle(0, 0, 256, 320)
        eye_color = 0x9FF6FF
        mouth_color = 0x66CFE0
        canvas.setColor(eye_color)
        if emotion == "sleepy":
            canvas.fillRectangle(54, 112, 54, 7)
            canvas.fillRectangle(148, 112, 54, 7)
        elif emotion == "wink":
            canvas.fillRectangle(54, 112, 54, 7)
            canvas.fillOval(148, 86, 54, 62)
        elif emotion == "angry":
            canvas.fillOval(54, 88, 54, 58)
            canvas.fillOval(148, 88, 54, 58)
            canvas.drawLine(46, 76, 108, 96)
            canvas.drawLine(210, 76, 148, 96)
        else:
            canvas.fillOval(54, 86, 54, 62)
            canvas.fillOval(148, 86, 54, 62)
        canvas.setColor(mouth_color)
        if emotion in ("happy", "love", "wink"):
            canvas.drawArc(78, 175, 100, 58, 10, 160)
        elif emotion == "sad":
            canvas.drawArc(78, 204, 100, 58, 190, 160)
        elif emotion == "surprised":
            canvas.drawOval(109, 181, 38, 54)
        elif emotion == "thinking":
            canvas.fillRectangle(96, 206, 64, 7)
        else:
            canvas.fillRectangle(96, 205, 64, 7)
        canvas.setColor(0xD9F8FA)
        canvas.drawText(emotion.upper(), 12, 292)

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
        self.log("stop", "tracks_zero", reason=reason)
        self.say("Stopped.")

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

    def update_approach(self):
        x, _, z = self.gps.getValues()
        target_x, target_z = self.target
        dx, dz = target_x - x, target_z - z
        distance = math.hypot(dx, dz)
        if distance <= APPROACH_DISTANCE + ARRIVAL_TOLERANCE:
            self.tracks(0.0, 0.0)
            self.action = None
            self.target = None
            self.set_emotion("happy")
            self.say("I have arrived.")
            self.log("approach", "arrived", distance=round(distance, 3))
            return
        yaw = self.imu.getRollPitchYaw()[2]
        desired_yaw = math.atan2(dz, dx)
        error = math.atan2(math.sin(desired_yaw - yaw), math.cos(desired_yaw - yaw))
        if abs(error) > 0.18:
            direction = 1.0 if error > 0 else -1.0
            self.tracks(-direction * TURN_SPEED, direction * TURN_SPEED)
        else:
            speed = min(MAX_SPEED, 0.7 + distance * 0.55)
            self.tracks(speed, speed)

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
            self.begin_approach((1.35, 1.15), "go_to_marker")
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
            self.mode = "tabletop" if self.mode == "floor" else "floor"
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
        """Accept a validated transcript from a future local ASR adapter.

        This function deliberately does not accept arbitrary LLM output as motion.
        """
        decision = parse_spoken_command(text)
        if not allow_action(decision, self.mode, self.emergency_stop):
            self.log("spoken_text", "rejected_by_safety_gate", transcript=text, action=decision.action)
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
        self.log("spoken_text", "conversation_needed", transcript=text)
        self.set_emotion("thinking")
        self.say("I heard you. The local dialogue service is not connected yet.")

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

    def run(self):
        while self.robot.step(TIME_STEP) != -1:
            key = self.keyboard.getKey()
            if key != -1:
                self.keyboard_command(key)
            if self.action == "approach":
                self.update_approach()
            elif self.action == "wave":
                self.update_wave()


if __name__ == "__main__":
    TulparController().run()
