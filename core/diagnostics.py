"""Format concise, privacy-conscious status lines for the Webots console."""


VISIBLE_DETAILS = (
    "trial_id",
    "scenario",
    "target",
    "expected",
    "selected",
    "reason",
    "distance_m",
    "pointing_error_deg",
    "response_time_s",
    "stopping_time_s",
    "emotion",
)


def format_status_event(event: dict) -> str:
    """Show an event and selected diagnostics without transcripts or reply text."""
    simulated_time = float(event.get("simulated_time_s", 0.0))
    mode = str(event.get("mode", "unknown"))
    command = str(event.get("command", "event"))
    outcome = str(event.get("outcome", "unknown"))
    line = f"[TULPAR {simulated_time:6.2f}s | {mode}] {command}: {outcome}"

    details = []
    for key in VISIBLE_DETAILS:
        value = event.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            value = " ".join(value.split())[:80]
        elif isinstance(value, float):
            value = f"{value:.3f}"
        details.append(f"{key}={value}")
    if details:
        line += " | " + ", ".join(details)
    return line
