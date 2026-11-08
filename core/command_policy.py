"""Deterministic safety gate between spoken text, model intent and TULPAR actions."""

from dataclasses import dataclass
import re


EMOTIONS = {
    "neutral", "happy", "sad", "surprised", "angry", "sleepy", "wink", "love", "thinking"
}
TARGET_ALIASES = {
    "target-A": ("target a", "marker a", "marked target a", "gold marker",
                 "gold target", "orange marker", "orange target", "yellow marker",
                 "yellow target"),
    "target-B": ("target b", "marker b", "marked target b", "purple marker",
                 "purple target", "violet marker", "violet target"),
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
    # Treat any clear spoken stop as an immediate safety/cancellation command,
    # even when ASR adds polite words or punctuation.
    if re.search(r"\bstop\b", phrase):
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


def explicit_navigation_target(text: str) -> str | None:
    """Resolve a named scene target only when the utterance clearly requests motion."""
    phrase = normalise(text)
    motion_request = re.search(
        r"\b(?:go|move|drive|walk|head|approach|navigate)\s+"
        r"(?:(?:over|up|right|straight)\s+)?(?:to|toward|towards)\b|"
        r"\bcome\s+(?:over\s+)?to\b|\bget\s+to\b|\btake\s+me\s+to\b",
        phrase,
    )
    if not motion_request:
        return None
    matches = [
        target_id for target_id, aliases in TARGET_ALIASES.items()
        if any(re.search(rf"\b{re.escape(alias)}\b", phrase) for alias in aliases)
    ]
    return matches[0] if len(matches) == 1 else None


def allow_action(decision: CommandDecision, mode: str, emergency_stop: bool) -> bool:
    """Apply the safety gate before commands reach the simulated actuators."""
    if decision.action == "stop":
        return True
    if emergency_stop:
        return False
    if decision.action in {"approach_operator", "approach_marker", "approach_object"}:
        return mode == "floor"
    return True
