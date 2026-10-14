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

The command policy accepts only the declared research scenarios: approach the operator, approach the indicated marker, stop, greeting, and the supported emotional face states. It blocks new movement during tabletop mode or an active emergency stop. A stop command remains permitted in either state.

The current command input is keyboard based. The future speech-recognition adapter must call the same policy function with an English transcript. The camera recognition sensor is configured to sample at one-second intervals, matching the report's planned vision rate. The controller compares the recognized image centres of the two marker labels with a simulated shoulder-to-fingertip ray and rejects missing or ambiguous detections. Keys `3` and `4` reposition the virtual fingertip for repeatable tests; this is a scene-controlled gesture proxy, not human pose estimation. A real camera/vision model remains future work.

The robot's Webots Supervisor control moves its pose between the floor start and the tabletop support when the mode key is pressed. That makes tabletop mode physically distinct in the simulation while keeping placement an explicit scene action between scenarios.
