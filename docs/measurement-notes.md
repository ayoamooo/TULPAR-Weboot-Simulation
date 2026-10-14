# Measurement notes

The 40 trials are a later validation stage. The event log records the first simulated movement command after an accepted approach command, the first shoulder movement after a greeting command, and the start of voice, face, and arm-pose outputs. These timestamps support simulated response-time and channel-start comparisons; they do not establish physical hardware performance.

- Movement response: valid command receipt to the first simulated drive command. The event log stores this as `movement.started.response_time_s`.
- Stop time: valid stop receipt to all four wheel sensors remaining below 0.05 rad/s for three consecutive samples. This is a simulated wheel-motion estimate, not a physical braking measurement.
- Front range safety: the Webots sonar surrogate treats the configured maximum-range return as a clear path, pauses and retries once on an invalid reading, stops on a second consecutive invalid reading, and stops for an obstacle within 0.25 m of the sensor. This is a controller fault-injection check, not a validation of the physical VL53L0X.
- Greeting response: valid greeting receipt to the first simulated shoulder movement. The event log stores this as `greeting.gesture_started.response_time_s`.
- Synchronisation: compare the simulated timestamps of `voice_output.started`, `face_display.emotion_started`, `arm_pose.emotion_started`, `movement.started`, and `greeting.gesture_started` where those channels are active. No physical actuator or audio onset is measured by Webots timestamps.

Pilot work must define and freeze route length, speed, final-distance tolerance, phrase variants, and sensor-invalid criteria before the main trial block begins.
