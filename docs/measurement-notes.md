# Measurement notes

The 40 trials are a later validation stage. This simulation records technical event timestamps but does not convert them into claimed physical hardware measurements.

- Movement response: valid command receipt to the first simulated drive command.
- Stop time: valid stop receipt to all four wheel sensors remaining below 0.05 rad/s for three consecutive samples. This is a simulated wheel-motion estimate, not a physical braking measurement.
- Front range safety: the Webots sonar surrogate treats the configured maximum-range return as a clear path, pauses and retries once on an invalid reading, stops on a second consecutive invalid reading, and stops for an obstacle within 0.25 m of the sensor. This is a controller fault-injection check, not a validation of the physical VL53L0X.
- Greeting response: valid greeting receipt to the start of the shoulder movement.
- Synchronisation: start-time differences between the active channels for the scenario.

Pilot work must define and freeze route length, speed, final-distance tolerance, phrase variants, and sensor-invalid criteria before the main trial block begins.
