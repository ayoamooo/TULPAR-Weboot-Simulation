"""Small deterministic gate between spoken text and TULPAR actions.

The local LLM may propose a reply and emotion, but it does not directly produce
motor commands. This module recognises only the scenarios defined in the report.
"""

from dataclasses import dataclass
import re


EMOTIONS = {
    "neutral", "happy", "sad", "surprised", "angry", "sleepy", "wink", "love", "thinking"
}


@dataclass(frozen=True)
class CommandDecision:
    action: str
    emotion: str | None = None


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def parse_spoken_command(text: str) -> CommandDecision:
    """Return an allowed action, or conversation when no declared command matches."""
    phrase = normalise(text)
    if phrase in {"stop", "stop now", "tulpar stop", "tulpar, stop"}:
        return CommandDecision("stop")
    if phrase in {"come to me", "come here", "tulpar come to me"}:
        return CommandDecision("approach_operator")
    if phrase in {"go to that marker", "go to the marker", "go to marker"}:
        return CommandDecision("approach_marker")
    if phrase in {"say hello", "hello tulpar", "tulpar say hello"}:
        return CommandDecision("greet", "happy")
    if phrase.startswith("show "):
        requested = phrase.removeprefix("show ").strip()
        if requested in EMOTIONS:
            return CommandDecision("emotion", requested)
    return CommandDecision("conversation")


def allow_action(decision: CommandDecision, mode: str, emergency_stop: bool) -> bool:
    """Apply the safety gate before commands reach the simulated actuators."""
    if decision.action == "stop":
        return True
    if emergency_stop:
        return False
    if decision.action in {"approach_operator", "approach_marker"}:
        return mode == "floor"
    return True
