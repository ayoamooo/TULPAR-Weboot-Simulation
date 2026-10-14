# TULPAR simulation runbook

This guide covers the planned 40-trial Webots evaluation. It records simulated outcomes only; it does not establish performance of the physical robot. Do not fill in results that were not observed in Webots.

## 1. Prepare the run

1. Open `worlds/tulpar_demo.wbt` in Webots R2025a or a compatible later release, then start the simulation in real-time mode.
2. Confirm that the robot, operator, both targets, and the test area are visible. Press `C` to cycle through the room overview, overhead, and robot-follow views.
3. Confirm that the range sensor is not in fault mode and that the emergency stop is clear. If either is active, clear it before starting a trial. `F` toggles the simulated sensor fault; `E` toggles the simulated emergency stop.
4. For voice-command trials, configure the local English Vosk model as described in [`voice-setup.md`](voice-setup.md), and confirm that the microphone is enabled in the Webots controller. Keyboard shortcuts can check the scene and action logic, but they do not count as voice-recognition trials.
5. The controller saves observed outcomes to `logs/technical-trial-results.csv` and event timings to `logs/tulpar-events.jsonl`. These files are created when the controller writes the first result or event. Keep the original files with the run; do not edit results to make a trial pass.

## 2. Controls

| Input | Action |
|---|---|
| `5` | Start the next unrecorded trial and hear its prompt |
| `6` | Record pass, only after the required behaviour has completed |
| `7` | Record fail; stop the tracks, cancel the arm wave, and end the active trial |
| `1` | Development shortcut: approach the recognised operator |
| `2` | Development shortcut: approach the marker selected from the simulated pointing pose |
| `3` / `4` | Set the simulated pointing pose toward target A / B |
| `S` | Stop the tracks; use the spoken word “stop” for a voice trial |
| `G` | Start the greeting wave; use “say hello” for a voice trial |
| `T` | Switch between floor and tabletop mode; only between trials |
| `C` | Cycle scene camera views |

The controller accepts fixed English voice commands independently of the local LLM: “come to me”, “go to that marker”, “stop”, and “say hello”. The dialogue model cannot command movement. Use the microphone for the planned command during a voice trial; use a keyboard shortcut only for setup or troubleshooting.

## 3. Run the planned trials

The plan is in [`../scenarios/technical-trials.csv`](../scenarios/technical-trials.csv). The controller selects the next unrecorded ID automatically. Start each trial with `5`, follow the spoken instruction, observe the outcome, then press `6` or `7`. A trial marked fail is complete in the plan and is not silently retried under the same ID.

| Trial IDs | Scenario and placement | Procedure | Pass condition |
|---|---|---|---|
| T01–T10 | Approach operator, floor | Press `5`; say “come to me” after the prompt | Robot starts moving only after the command and reaches the operator’s recognised approach point without a safety rejection |
| T11–T20 | Approach marked target, floor | Press `5`; use `3` or `4` as named in the prompt; then say “go to that marker” | Robot selects the prompted target and reaches its approach point; an incorrect target is a fail even if it moves |
| T21–T30 | Stop, floor | Press `5`; wait until the tracks are visibly moving; say “stop” | Tracks stop following the command and the controller confirms wheel-speed stability; do not use `S` to score a voice trial |
| T31–T35 | Greeting, tabletop | Switch to tabletop mode with `T` before starting T31; press `5`; say “say hello” | Tracks stay locked; spoken greeting, face response, and non-contact arm wave complete |
| T36–T40 | Greeting, floor | Switch back to floor mode with `T` before starting T36; press `5`; say “say hello” | Tracks remain stopped; spoken greeting, face response, and non-contact arm wave complete |

For T11–T20, target A and target B alternate, five each. Use the key stated in the trial prompt to position the virtual pointing gesture. That key is a repeatable simulator input, not a test of real human gesture recognition.

If a trial fails or cannot safely continue, press `7`. The controller cancels the active simulated motion or gesture before writing the fail row. If a safety fault occurs, stop the simulation and resolve it before continuing. Do not mark pass until the stated criterion is visible and the relevant controller event has been recorded.

## 4. Review the recorded data

After the run, from the repository root execute:

```powershell
python -m core.trial_analysis
```

The summary uses only rows and events that were recorded. It reports unmeasured values as unavailable rather than filling gaps with estimates. Check that each planned ID appears once in the results CSV and compare the logged outcome with the visible run before using any figures in the report.

## 5. Simulation limits

- Voice trials depend on the local Vosk model and microphone working in the Webots controller process. Without them, keyboard controls test action logic only.
- The marker gesture and target labels are simulated. The run does not validate a physical camera’s human-pose or pointing accuracy.
- The approach uses Webots recognition and simulator pose data as documented in the README; it does not demonstrate fully autonomous navigation in an unstructured room.
- Material friction values, sensing behaviour, stopping measurements, and timing remain simulation results or provisional inputs. They must not be presented as measured physical hardware performance.
