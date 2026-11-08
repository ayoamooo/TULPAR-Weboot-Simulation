"""Named, vision-recognisable objects that the virtual robot may approach."""


SCENE_TARGETS = {
    "target-A": {
        "def_name": "MARKER_A",
        "model": "target-A",
        "spoken_name": "yellow marker",
        "aliases": (
            "target a", "marker a", "marked target a", "gold marker",
            "gold target", "gold object", "orange marker", "orange target",
            "orange object", "yellow marker", "yellow target", "yellow object",
        ),
    },
    "target-B": {
        "def_name": "MARKER_B",
        "model": "target-B",
        "spoken_name": "purple marker",
        "aliases": (
            "target b", "marker b", "marked target b", "purple marker",
            "purple target", "purple object", "violet marker", "violet target",
            "violet object",
        ),
    },
    "scene-bench": {
        "def_name": "SCENE_BENCH",
        "model": "scene-bench",
        "spoken_name": "bench",
        "aliases": ("bench", "the bench", "seat", "the seat"),
    },
    "scene-plant": {
        "def_name": "SCENE_PLANT",
        "model": "scene-plant",
        "spoken_name": "potted plant",
        "aliases": (
            "plant", "the plant", "potted plant", "the potted plant",
            "flower pot", "the flower pot",
        ),
    },
}


TARGET_ALIASES = {
    target_id: target["aliases"] for target_id, target in SCENE_TARGETS.items()
}


def target_prompt_lines() -> str:
    """Return stable target descriptions for a local dialogue system prompt."""
    return "; ".join(
        f'{target_id} is the {target["spoken_name"]} '
        f'(also called {", ".join(target["aliases"])})'
        for target_id, target in SCENE_TARGETS.items()
    )


def validate_scene_navigation(
    transcript: str,
    target_id: str,
    mode: str,
    emergency_stop: bool,
    visible_models,
    recognition_age_s: float | None,
    max_recognition_age_s: float = 1.25,
) -> str | None:
    """Return a rejection reason, or ``None`` when a proposed approach is safe to start."""
    target = SCENE_TARGETS.get(target_id)
    if target is None:
        return "unknown_target"
    if explicit_target := _spoken_target(transcript):
        if explicit_target != target_id:
            return "intent_target_mismatch"
    else:
        return "intent_not_explicit"
    if mode != "floor":
        return "rejected_tabletop"
    if emergency_stop:
        return "rejected_emergency_stop"
    if recognition_age_s is None or recognition_age_s > max_recognition_age_s:
        return "recognition_frame_stale"
    if target["model"] not in set(visible_models):
        return "target_not_visible"
    return None


def _spoken_target(transcript: str) -> str | None:
    from core.command_policy import explicit_navigation_target

    return explicit_navigation_target(transcript)

