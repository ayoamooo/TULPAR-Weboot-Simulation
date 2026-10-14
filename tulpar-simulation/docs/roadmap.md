# Development roadmap

1. **Scene and robot model** — source includes a 0.60 m target height, a screen surface driven by the Webots Display texture, a forward-facing camera, and two recognition-labelled markers; visual verification is pending.
2. **Physics and movement** — four simulated drive wheels are connected to the controller. The controller now uses X/Y as the floor plane; contact, wheel direction, and braking still need Webots runtime verification.
3. **Interaction state** — the mode key relocates the simulated robot between the floor start point and the table support. This is a between-scenario placement action, not autonomous boarding. Stop, emergency-stop state, animated face states, greeting, and one-retry range-sensor fail-safe are implemented in source.
4. **Local voice and dialogue** — Vosk microphone capture, command-policy routing, background local Ollama dialogue, and Webots speech output are connected in source. Runtime validation still requires a local Vosk model, running Ollama service, and Webots installation.
5. **Vision and pointing** — one-second Webots recognition selects a labelled marker from the simulated shoulder-to-fingertip image ray; missing and ambiguous targets are rejected. Real human pose estimation remains future work.
6. **Pilot and trial logging** — define fixed pilot parameters, then run the 40 reported technical trials.
