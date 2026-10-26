# TULPAR 3D walkthrough

Open `worlds/tulpar_showcase.wbt` in Webots R2025a, or run `START-TULPAR.cmd`. The showcase begins automatically. Click the 3D view before using keyboard controls; reload the world to replay if keyboard input is unavailable.

| Key | Action |
| --- | --- |
| B | Restart the walkthrough |
| R | Restart and record an MP4 |
| C | Cycle external, overview, overhead and close-follow cameras |
| 1 | Approach the operator |
| 3 / 4, then 2 | Set a simulated pointing pose for marker A / B, wait for a camera update, then approach |
| S | Stop the tracks |
| G | Perform a non-contact greeting wave |
| T | Change floor / tabletop placement between trials |

The scripted walkthrough demonstrates the four planned command scenarios: approach the operator, approach the marked target indicated by the operator, stop during movement, and greet. Greeting is shown in both floor and tabletop placements while the tracks remain stopped. The emotion preview shows neutral, happy, sad, surprised, angry, sleepy, wink, love and thinking expressions with the associated arm poses. The preview states are not extra trial results. Object delivery and physical contact are excluded.

## Scene screenshots

The screenshots document representative Webots states. They do not show outcomes from the planned 40 technical trials or establish physical performance. The coloured axes in the stop image are Webots' editor selection gizmo.

### Stop response

![TULPAR stopped in the floor scene](assets/stop-confirmed.jpg)

The stop command has been received and the simulated tracks are stationary.

### Greeting in floor mode

![TULPAR greeting in floor mode](assets/floor-greeting.jpg)

Spoken greeting, animated face and non-contact arm wave with the robot on the floor.

### Greeting in tabletop mode

![TULPAR greeting in tabletop mode](assets/tabletop-greeting.jpg)

The same greeting with the drive disabled in tabletop placement.

### Expression previews

![TULPAR surprised expression preview](assets/emotion-surprised.jpg)

Surprised face with raised arm pose.

![TULPAR sad expression preview](assets/emotion-sad.jpg)

Sad face with lowered arm pose.

## Model and simulation limits

The room has a 0.5 m reference grid, carpet test patch, tabletop support, operator figure and two marked targets. The model follows the reference design's tracked base, panelled body, smartphone face, webcam, paired arms and fixed claws. Grille, panel fasteners, range-sensor housing, wheel hubs and tread cleats are conceptual details, not a fabrication specification.

Walkthrough commands are scripted English text passed through the command policy, and Webots synthesises fixed replies. This run does not use microphone recognition or the local LLM. Target selection uses Webots recognition objects and simulator positions; the pointing pose is simulated, not a live human pose estimate. The mobile base uses four driven wheels under cosmetic tracks, not a deformable continuous belt. The face / voice / arm and movement sequence is an integration demonstration, not evidence of validated hardware.

The controller records a range-based stand-off as `front_sensor_to_surface`. A navigation fallback is logged as `simulator_centre_distance`; these are different reference points and must not be combined as if they were the same measurement. Simulated stopping and sensor readings do not establish physical braking performance or hardware safety.

The walkthrough does not populate the 40-trial results CSV. Use the separate procedure in [simulation-runbook.md](simulation-runbook.md) to run and record simulated trials. Geometry, friction, masses and joint limits remain assumptions that require hardware validation. Dataset-level audio results and local model timings are documented separately in [the audio evaluation](../research/audio_eval/README.md) and [the local model smoke check](local-model-smoke-check.md); neither should be reported as integrated robot-trial performance.

## Recording status

The latest recorded walkthrough is about 97.5 seconds long, silent, and contains a black interval from approximately 75 to 90 seconds. It is not suitable as a finished presentation video. The Webots interactive 3D animation and its CSS, W3D and JSON files were exported together, but browser playback has not been independently verified. Keep those files beside one another under `outputs/`. Generated recordings and simulation logs are excluded from Git; consult [showcase-run.md](showcase-run.md) for the run details and limitations.
