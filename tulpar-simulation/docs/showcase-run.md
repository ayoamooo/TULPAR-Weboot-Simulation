# Webots walkthrough run record

Date: 20 October 2026. This is a scripted Webots simulation walkthrough, not a physical-robot test and not a set of report trial results.

## What completed

- The controller completed the operator-approach, indicated-marker approach, moving-stop, floor greeting, and tabletop greeting sequence.
- The operator approach ended at a 0.499 m front-sensor-to-surface stand-off. The indicated-marker navigation fallback ended at a 0.579 m simulator-centre distance. These values use different reference points and are not directly comparable.
- The simulated stop detector reported 0.096 s from the stop command until wheel sensors reported zero rotation. This is a simulator observation and does not establish physical stopping performance.
- Both greeting modes kept the tracks stopped while the face, arm pose, and fixed spoken reply were triggered.
- The preview showed surprised, sad, angry, sleepy, wink, love, thinking, and happy expressions. The initial neutral expression is also supported. The corresponding arm poses were triggered with the face states.
- The sequence reached 97.056 s of simulated time and exported 17 main-view PNG captures plus 17 robot-camera PNG captures under `logs/showcase`.

## Video status

The latest completed real-time run produced `outputs/TULPAR-walkthrough.mp4`: H.264, 1280 × 720, 31.25 fps, 97.536 s, 69,719,161 bytes. It contains video only; no audio stream was recorded. Frame inspection found a black interval from approximately 75 to 90 seconds, so this file must not be treated as a finished presentation video.

The same run exported Webots' interactive 3D animation to `outputs/TULPAR-walkthrough-interactive.html` and its companion CSS, W3D scene, and JSON animation files in the same folder. The four files total 821,985 bytes; the JSON contains 3,034 animation frames. The export returned success and the scene and JSON files parse locally, but the rendered browser playback has not been independently inspected. Keep the files together when opening or copying the animation. Webots warns that browser local-file CORS settings can prevent an exported animation from loading; use the in-app browser tab or follow the official Webots guide if the page shows a loading error. The MP4 has no audio, while live Webots can speak the scripted replies when its Speaker is enabled.

An earlier batch/fast attempt produced a zero-byte temporary MP4; the output-preservation check prevented that attempt from replacing the then-valid video. A later real-time run completed the interactive 3D export and produced the MP4 described above. A separate MP4-only retry has not yet produced a completed recording event or a replacement file.

## Limits

The walkthrough supplies scripted English transcripts and fixed spoken text; it does not use microphone recognition or the local LLM. The pointing and marker selection use Webots recognition objects and simulator coordinates. The scene does not implement real human-pose estimation, autonomous obstacle avoidance, or deformable tracks. The simulation run did not create any of the planned 40 trial records.
