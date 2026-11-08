"""Deterministic safety gate between spoken text, model intent and TULPAR actions."""

from dataclasses import dataclass
import re

from core.scene_targets import TARGET_ALIASES


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
    phrase = re.sub(r"[^a-z0-9\s'-]", " ", normalise(text))
    phrase = normalise(phrase)
    # Safety controls are deliberately matched before general conversation and
    # before the local model. Avoid treating incidental phrases such as
    # "don't stop" as a command.
    if re.fullmatch(
        r"(?:please )?(?:(?:activate|engage|enable|turn on) )?emergency stop",
        phrase,
    ):
        return CommandDecision("emergency_on")
    if re.fullmatch(
        r"(?:please )?(?:clear|release|disengage|disable|turn off) emergency stop",
        phrase,
    ):
        return CommandDecision("emergency_off")
    if _is_stop_request(phrase) or phrase in {
        "don't move", "do not move", "please don't move", "please do not move",
        "stay still", "stay there", "stay put", "please stay there", "please stay put",
    }:
        return CommandDecision("stop")

    if _is_mode_request(phrase, "floor"):
        return CommandDecision("mode_floor")
    if _is_mode_request(phrase, "tabletop"):
        return CommandDecision("mode_tabletop")

    if _is_operator_approach_request(phrase):
        return CommandDecision("approach_operator")
    if phrase in {
        "say hello", "say hi", "hello tulpar", "hi tulpar", "tulpar say hello",
        "tulpar say hi", "wave hello", "give me a wave", "greet me",
    }:
        return CommandDecision("greet", "happy")
    emotion_match = re.fullmatch(r"(?:show|look|act|be) (?:me )?([a-z]+)(?: face)?", phrase)
    if emotion_match and emotion_match.group(1) in EMOTIONS:
        return CommandDecision("emotion", emotion_match.group(1))
    return CommandDecision("conversation")


def _is_stop_request(phrase: str) -> bool:
    command = r"(?:stop|halt|freeze|cancel|abort)(?: now| moving| the robot| the tracks)?"
    return bool(re.fullmatch(
        rf"(?:please )?(?:tulpar )?{command}|"
        rf"(?:please )?(?:can you|could you|would you) (?:please )?{command}",
        phrase,
    ))


def _is_operator_approach_request(phrase: str) -> bool:
    return bool(re.fullmatch(
        r"(?:please )?(?:tulpar )?(?:come|move|drive|approach) "
        r"(?:over |closer )?(?:here|me|to me|toward me|towards me|(?:the )?(?:operator|person|human))|"
        r"(?:please )?(?:tulpar )?come closer",
        phrase,
    ) or re.fullmatch(
        r"(?:please )?(?:can you|could you|would you) (?:please )?"
        r"(?:come|move|drive|approach) (?:over |closer )?(?:here|me|to me|toward me|towards me|(?:the )?(?:operator|person|human))|"
        r"(?:please )?(?:can you|could you|would you) (?:please )?come closer",
        phrase,
    ))


def _is_mode_request(phrase: str, mode: str) -> bool:
    mode_phrase = rf"{mode}(?: mode)?"
    patterns = (
        rf"(?:please )?(?:switch|change|set|select|enter|activate|use) to {mode_phrase}",
        rf"(?:please )?change into {mode_phrase}",
        rf"(?:please )?(?:switch|change|set|select|put) (?:the robot )?(?:to )?{mode_phrase}",
    )
    return any(re.fullmatch(pattern, phrase) for pattern in patterns)


def explicit_navigation_target(text: str) -> str | None:
    """Resolve a named scene target only when the utterance clearly requests motion."""
    phrase = normalise(text)
    if not is_scene_navigation_request(phrase):
        return None
    matches = [
        target_id for target_id, aliases in TARGET_ALIASES.items()
        if any(re.search(rf"\b{re.escape(alias)}\b", phrase) for alias in aliases)
    ]
    return matches[0] if len(matches) == 1 else None


def is_scene_navigation_request(text: str) -> bool:
    """Recognize direct movement requests even when the target is vague or unknown."""
    phrase = normalise(text)
    movement = (
        r"(?:go|move|drive|walk|head|navigate)(?: over| up| closer)? "
        r"(?:to|toward|towards|near|up to)"
        r"|approach|come(?: over)? to|get(?: closer)? to|take me(?: over)? to"
    )
    prefixes = (
        rf"(?:please )?(?:tulpar[, ]+)?{movement}",
        rf"(?:can|could|would) you (?:please )?{movement}",
        rf"i (?:want|would like) you to {movement}",
    )
    return any(re.match(rf"^{prefix}\b", phrase) for prefix in prefixes)


def allow_action(decision: CommandDecision, mode: str, emergency_stop: bool) -> bool:
    """Apply the safety gate before commands reach the simulated actuators."""
    if decision.action == "stop":
        return True
    if emergency_stop:
        return False
    if decision.action in {"approach_operator", "approach_marker", "approach_object"}:
        return mode == "floor"
    return True
