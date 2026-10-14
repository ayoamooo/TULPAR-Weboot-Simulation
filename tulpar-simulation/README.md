# TULPAR virtual demonstration

This folder contains the new Webots simulation source for the TULPAR research prototype. It is separate from the report and its drawings.

The first scene represents a controlled university demonstration room. It includes a floor route, carpet test area, tabletop support, operator figure, two marked targets, and a 0.6 m tracked robot based on the assembly concept.

## Intended behaviour

- Floor mode: `come to me`, `go to marker`, and `stop` control the tracked base.
- Tabletop mode: the tracks remain locked; speech, face states, and arm gestures remain available.
- `say hello` runs a non-contact wave with the tracks stopped.
- The controller records command, mode, outcome, and simulated timing in `logs/tulpar-events.jsonl`.

The initial controller uses keyboard input while the microphone, local speech recognition, and local LLM adapters are added after the scene can be launched and verified. Keyboard input is only a development control path. All future transcripts pass through `core/command_policy.py`; a language model cannot issue unrestricted drive commands.

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

The scene is a software simulation. It does not establish physical braking distance, power consumption, or hardware safety.

Marker selection uses Webots recognition labels and the image-space alignment between simulated shoulder and fingertip markers. Keys `3` and `4` move the virtual fingertip to create repeatable test poses; this is a simulation input, not real-world pointing detection or a learned vision model. If gesture markers or targets are not visible, or alignment is ambiguous, the controller rejects the command instead of choosing a fixed target.

## Trial plan

`scenarios/technical-trials.csv` lists each of the 40 planned trials separately. Regenerate it with `python -m core.trial_protocol` after changing the allocation. It contains inputs only; results and timestamps must come from actual simulation runs. The 10 greeting trials are split evenly between tabletop and floor placement.
