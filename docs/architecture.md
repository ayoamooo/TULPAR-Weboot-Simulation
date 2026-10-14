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

The first milestone uses keyboard input only to check the scene and controller. The future speech-recognition adapter must call the same policy function with an English transcript. The vision layer will later propose a marked target from the robot camera; navigation must still validate the target and safety state before motion begins.
