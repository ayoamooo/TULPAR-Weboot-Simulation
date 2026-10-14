# Architecture

TULPAR uses separate layers so a dialogue model cannot directly command the simulated drive.

```text
operator microphone
        |
local speech recognition
        |
command policy ----> local dialogue model ----> response text and emotion
        |
Webots controller ----> tracks, arm joints, face display, speaker
        |
event log and trial record
```

The command policy accepts only the declared research scenarios: approach the operator, approach the indicated marker, stop, greeting, and the supported emotional face states. It blocks new movement during tabletop mode or an active emergency stop. A stop command remains permitted in either state. The approach-to-operator scenario requires a fresh camera recognition of the operator before it reads the operator's Webots world pose as the navigation target; the pose is simulator ground truth, not a vision-model distance estimate.

Keyboard input remains available for repeatable development tests. An optional Vosk microphone adapter provides English transcripts to the same command policy. Allow-listed movement commands bypass the dialogue model; ordinary conversation samples at most one camera image per second, requests a local Ollama vision summary, then submits the transcript and visual context to the local dialogue model on a background thread. The text model's structured response contains only a spoken reply and a supported emotion. Webots recognition samples at one-second intervals and selects a labelled marker from the simulated shoulder-to-fingertip image ray; keys `3` and `4` reposition the virtual fingertip for repeatable tests. This is a scene-controlled gesture proxy, not human pose estimation. See `voice-setup.md` for model and runtime requirements.

The robot's Webots Supervisor control moves its pose between the floor start and the tabletop support when the mode key is pressed. That makes tabletop mode physically distinct in the simulation while keeping placement an explicit scene action between scenarios.

During approach, the front sonar surrogate is checked before each drive update. A maximum-range reading means no hit within the configured 1.5 m range; one invalid sample pauses motion for a retry, and a second consecutive invalid sample or a near obstacle stops the approach. Key `F` injects a persistent invalid reading to test the retry and stop path. This simulates control logic only and does not validate a VL53L0X device.
