# TULPAR virtual demonstration

For the automatic 3D walkthrough, run **START-TULPAR.cmd** or open **worlds/tulpar_showcase.wbt** in Webots R2025a. Press **B** to replay and **C** to change the camera. See the [walkthrough guide](docs/showcase.md).

The latest scripted run exported a silent MP4 and a Webots interactive animation under `outputs/`. The MP4 contains a black interval and is not presentation-ready; browser playback of the interactive export has not been verified. See the [walkthrough run record](docs/showcase-run.md).

This folder contains simulation source for the TULPAR research prototype. It is separate from the dissertation report and assembly drawings.

## Intended behaviour

- Floor mode: `come to me`, `go to marker`, and `stop` control the tracked base.
- Tabletop mode: the tracks are disabled; speech, facial animation, and arm gestures remain available.
- `say hello` triggers a non-contact wave with the tracks stopped.
- The controller logs command, mode, outcome, response timing, and channel-start timestamps to `logs/tulpar-events.jsonl`.
- Console logs contain decision details such as target, mode, and rejection reason; they do not print spoken transcripts or generated replies.

The controller supports keyboard development controls and an optional local voice path. Microphone speech is transcribed by Vosk when `TULPAR_VOSK_MODEL` points to a local English model directory. Allow-listed commands go directly through `core/command_policy.py`. Ordinary conversation sends a camera frame to local Ollama for scene context (`qwen2.5vl:3b`) and requests a dialogue response (`qwen3:4b`). The text model may return a reply and supported emotion only; it cannot issue movement or actuator commands. Webots' Speaker reads the reply aloud. See [voice setup](docs/voice-setup.md).

## Development scene

Open `worlds/tulpar_demo.wbt` in Webots and run it in real-time mode. The room includes a floor route, a carpet patch, a tabletop support, an operator figure, two marked targets, and a 0.6 m tracked robot based on the assembly concept.

| Key | Action |
| --- | --- |
| 1 | Approach the operator |
| 2 | Approach the marker indicated by the simulated pointing pose |
| 3 / 4 | Set the simulated fingertip pose toward marker A / B; press 2 to test selection |
| S | Stop |
| G | Non-contact greeting wave |
| T | Switch between floor and tabletop modes |
| H, A, D, P, Y, W, O, I, N | Happy, angry, sad, surprised, sleepy, wink, love, thinking, neutral |
| E | Simulated emergency stop |
| F | Toggle invalid range-sensor fault for retry/stop check |
| C | Cycle side-on, overview, overhead, and robot-follow views |
| 5 | Start the next planned technical trial in its required placement mode |
| 6 / 7 | Record pass / fail after checking the stated outcome |

## Trial plan and evidence

`scenarios/technical-trials.csv` lists the 40 planned trials separately. It contains the test allocation, not results. The 10 greetings are split evenly between tabletop and floor placements. Regenerate the plan with `python -m core.trial_protocol` after changing the allocation.

The controller writes completed trial outcomes to `logs/technical-trial-results.csv`. Unrun trials have no result row. Use the [simulation runbook](docs/simulation-runbook.md) to place the robot, execute, and record each scenario. `python -m core.trial_analysis` summarises recorded outcomes; missing or unmeasured values remain unavailable.

A separate classical baseline for Speech Commands and speech-only RAVDESS is documented in [research/audio_eval](research/audio_eval/README.md). One-off local dialogue and vision latency checks are recorded in [local-model-smoke-check.md](docs/local-model-smoke-check.md). Dataset results and one-off model timings are not TULPAR system performance or results from the 40 planned robot trials.

## Scope and limitations

The simulation uses provisional floor, carpet, and tabletop friction settings; it does not establish physical braking distance, power use, or hardware safety. The operator approach uses the Webots world pose as simulator ground truth. Marker selection uses simulator recognition labels and a simulated fingertip pose, not live human pose estimation or a trained vision model. The mobile base uses four driven wheels beneath cosmetic tracks. Geometry, friction, masses, and joint limits require hardware validation.

## Screenshots

See the [Webots screenshot gallery](docs/showcase.md#scene-screenshots) for stop, greeting, and expression-preview images. The images show representative simulation states, not trial outcomes.
