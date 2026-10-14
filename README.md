# TULPAR virtual demonstration

This folder contains the new Webots simulation source for the TULPAR research prototype. It is separate from the report and its drawings.

The first scene represents a controlled university demonstration room. It includes a floor route, carpet test area, tabletop support, operator figure, two marked targets, and a 0.6 m tracked robot based on the assembly concept.

## Intended behaviour

- Floor mode: `come to me`, `go to marker`, and `stop` control the tracked base.
- Tabletop mode: the tracks remain locked; speech, animated face expressions, and arm gestures remain available.
- `say hello` runs a non-contact wave with the tracks stopped.
- The controller records command, mode, outcome, response timing, and channel-start timestamps in `logs/tulpar-events.jsonl`.
- The Webots console shows compact event lines with allowed decision details such as target, mode, and rejection reason. It does not print spoken transcripts or generated reply text.

The controller supports keyboard development controls and an optional local voice path. Microphone speech is transcribed by Vosk when `TULPAR_VOSK_MODEL` points to a local English model directory. Allow-listed commands go directly through `core/command_policy.py`; ordinary conversation sends one camera frame per voice turn (capped at one per second) to local Ollama (`qwen2.5vl:3b`) for scene context, then asynchronously asks `qwen3:4b` for a response. The text model can return only a reply and a supported emotion, never a motion command. Webots' Speaker reads replies aloud.

## Planned launch

Open `worlds/tulpar_demo.wbt` in Webots and run the simulation in real-time mode. The scene needs Webots R2025a or a compatible later release.

Keys:

- `1` — approach the operator.
- `2` — approach the marker indicated by the simulated pointing pose.
- `3` / `4` — set the simulated operator fingertip pose towards marker A / B; then press `2` to test camera-based selection.
- `S` — stop.
- `G` — greeting wave.
- `T` — switch between floor and tabletop modes.
- `H`, `A`, `D`, `P`, `Y`, `W`, `O`, `I`, `N` — happy, angry, sad, surprised, sleepy, wink, love, thinking, neutral.
- `E` — simulated emergency stop.
- `F` — toggle an invalid-range-sensor fault for the retry/stop check.
- `C` — cycle the overview, overhead, and robot-following scene views.
- `5` — start the next planned technical trial (requires the listed placement mode).
- `6` / `7` — record the active trial as pass / fail after checking its stated outcome.

The scene is a software simulation. It does not establish physical braking distance, power consumption, or hardware safety.

For microphone and local dialogue setup, see [`docs/voice-setup.md`](docs/voice-setup.md). Without a Vosk model directory, microphone input is disabled and keyboard controls remain available. Without the Ollama service, ordinary conversation reports an unavailable local model; fixed commands such as `stop` continue to be handled by the controller.

Approach to the operator requires a fresh camera recognition of the operator. The simulation then uses the operator's Webots world pose for navigation; that pose is simulator ground truth rather than a vision-model estimate. Marker selection uses Webots recognition labels and the image-space alignment between simulated shoulder and fingertip markers. Keys `3` and `4` move the virtual fingertip to create repeatable test poses; this is a simulation input, not real-world pointing detection or a learned vision model. If the operator, gesture markers, or targets are not visible, or alignment is ambiguous, the controller rejects the command instead of choosing a fixed target.

## Trial plan

`scenarios/technical-trials.csv` lists each of the 40 planned trials separately. Regenerate it with `python -m core.trial_protocol` after changing the allocation. It contains inputs only; results and timestamps must come from actual simulation runs. The 10 greeting trials are split evenly between tabletop and floor placement.

The controller writes completed outcomes to `logs/technical-trial-results.csv`. Start a trial with `5`; the robot is reset to the same floor or tabletop pose between trials. For stop trials, it begins approaching the operator so you can issue `stop` while the tracks are moving. Use `6` for pass or `7` for fail after observing the outcome. A pass is rejected until the scenario reaches its measured success condition. The CSV records the planned scenario and elapsed Webots simulation time; an unrun trial has no result row. Existing result rows are kept and the controller resumes at the first unrecorded trial ID.

The controller event log tags scenario events with the active trial ID. The marker-selection block alternates the expected target evenly between target A and target B; the trial prompt tells you which simulated pointing-pose key to use. After running trials, `python -m core.trial_analysis` prints counts, observed pass rates, target-selection accuracy, response-time summaries, and channel-start spreads from those files. Empty or unmeasured quantities stay unavailable; the analysis does not invent values. The greeting voice now starts with the face response, just before the first simulated arm movement.
