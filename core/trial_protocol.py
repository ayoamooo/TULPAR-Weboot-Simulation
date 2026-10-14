"""The 40 planned simulation trials, separate from observed results.

This module fixes the trial allocation without inventing measurements. A run can
be recorded later against one of these IDs, including failed attempts.
"""

from dataclasses import dataclass
import csv
from pathlib import Path


@dataclass(frozen=True)
class Trial:
    trial_id: str
    scenario: str
    placement: str
    command: str
    target: str


def build_plan() -> list[Trial]:
    groups = (
        (10, "approach_operator", "floor", "come to me", "operator"),
        (10, "approach_marked_target", "floor", "go to that marker", "indicated marker"),
        (10, "stop", "floor", "stop", "moving robot"),
        (5, "greeting", "tabletop", "say hello", "none"),
        (5, "greeting", "floor", "say hello", "none"),
    )
    trials: list[Trial] = []
    for count, scenario, placement, command, target in groups:
        for _ in range(count):
            trials.append(Trial(f"T{len(trials) + 1:02d}", scenario, placement, command, target))
    return trials


def write_plan(path: Path) -> None:
    """Write planned inputs only; outcome and timing belong to actual runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("trial_id", "scenario", "placement", "command", "target"))
        for trial in build_plan():
            writer.writerow((trial.trial_id, trial.scenario, trial.placement, trial.command, trial.target))


if __name__ == "__main__":
    write_plan(Path(__file__).resolve().parents[1] / "scenarios" / "technical-trials.csv")
