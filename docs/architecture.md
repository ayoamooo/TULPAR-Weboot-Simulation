# Architecture

TULPAR uses separate layers so a dialogue model cannot directly command the simulated drive.

```text
operator microphone
        |
local speech recognition
        |
immediate Stop / emergency gate -------------------> brake + invalidate pending reply
        |
deterministic command policy
        | direct command                 | named-object command       | conversation
        |                                |                            |
mode / greeting / emotion              |                      local dialogue model
                                       |                      reply + emotion
                                       +-------------+--------------+
                                                     |
                        camera visibility + floor mode + stop safety gates
                                                     |
Webots controller ----------------------> tracks, arms, face, speaker
        |
aggregate technical event log (no transcript or audio)
```

The local model handles a short conversational reply and supported facial emotion. It cannot output coordinates or actuator values. Explicit movement commands to named scene objects are parsed locally without an LLM call; the controller starts an approach only when the target is registered and freshly visible, floor mode is active, and the emergency stop is clear. Vosk partial results are checked for spoken Stop before model inference. `stop` cancels the active action; `emergency stop` also latches the movement interlock until the operator says `clear emergency stop`. Both invalidate queued and in-flight results, so a delayed response cannot restart an action. Mode changes, greeting and direct emotion requests can also be spoken; keyboard inputs remain for development and repeatable test controls.

Keyboard input remains available for repeatable development checks. Vosk sends English transcripts to the controller; the local interaction model runs on a worker thread, while Webots keeps its simulation loop responsive. A short bounded conversation history exists only in RAM. The selected model service may be Ollama or llama.cpp's local OpenAI-compatible endpoint. The controller logs event types and outcomes, not the recognized words, generated reply, audio, or conversation history. Webots recognition samples at one-second intervals; keys `3` and `4` reposition the virtual fingertip for the separate repeatable marker-pointing check. This is a scene-controlled gesture proxy, not human pose estimation. See `voice-setup.md` for model and runtime requirements.

The robot's Webots Supervisor control moves its pose between the floor start and the tabletop support when the operator requests a mode change by voice. That makes tabletop mode physically distinct in the simulation while keeping placement an explicit scene action between scenarios.

During approach, the front sonar surrogate is checked before each drive update. A maximum-range reading means no hit within the configured 1.5 m range; one invalid sample pauses motion for a retry, and a second consecutive invalid sample or a near obstacle stops the approach. Key `F` injects a persistent invalid reading to test the retry and stop path. This simulates control logic only and does not validate a VL53L0X device.
