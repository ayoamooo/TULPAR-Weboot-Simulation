"""Fixed external camera for reviewable 3D captures of the TULPAR demo."""

from pathlib import Path
import os

from controller import Robot


STEP_MS = 32
CAPTURE_INTERVAL_S = 0.25

robot = Robot()
camera = robot.getDevice("observer camera")
camera.enable(64)
capture_dir = Path(os.environ.get("TULPAR_CAPTURE_DIR", "logs/auto-demo"))
capture_dir.mkdir(parents=True, exist_ok=True)
next_capture = 0.5
frame_index = 0

while robot.step(STEP_MS) != -1:
    now = robot.getTime()
    if now + 1e-9 < next_capture:
        continue
    filename = capture_dir / f"frame_{frame_index:03d}.png"
    camera.saveImage(str(filename), 90)
    frame_index += 1
    next_capture += CAPTURE_INTERVAL_S
