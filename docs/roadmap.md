# Development roadmap

1. **Scene and robot model** — source includes a 0.60 m target height, a screen surface driven by the Webots Display texture, a forward-facing camera, and two recognition-labelled markers; visual verification is pending.
2. **Physics and movement** — four simulated drive wheels are connected to the controller. The controller now uses X/Y as the floor plane; contact, wheel direction, and braking still need Webots runtime verification.
3. **Interaction state** — the mode key relocates the simulated robot between the floor start point and the table support. This is a between-scenario placement action, not autonomous boarding. Stop, emergency-stop state, face states, and greeting are in the controller.
4. **Local voice and dialogue** — add microphone capture, local speech recognition, local dialogue, and local text-to-speech.
5. **Vision and pointing** — recognition is configured at one-second intervals and the two targets are labelled. Target selection from the operator's pointing gesture and ambiguity rejection remain to be implemented.
6. **Pilot and trial logging** — define fixed pilot parameters, then run the 40 reported technical trials.
