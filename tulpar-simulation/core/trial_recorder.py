"""Record observed outcomes for the pre-defined technical trial plan.

The recorder never fills in outcomes or timings for the operator. Only trials
explicitly started and marked pass/fail are written to the results CSV.
"""

import csv
from pathlib import Path

from core.trial_protocol import Trial, build_plan


FIELDS = (
    "trial_id", "scenario", "placement", "command", "target", "outcome",
    "started_sim_time_s", "finished_sim_time_s", "duration_s",
)


class TrialRecorder:
    def __init__(self, results_path: Path, trials: list[Trial] | None = None):
        self.results_path = Path(results_path)
        self.trials = trials if trials is not None else build_plan()
        self.current: Trial | None = None
        self.started_at: float | None = None
        self.completed_ids = self._read_completed_ids()

    def _read_completed_ids(self) -> set[str]:
        if not self.results_path.exists():
            return set()
        with self.results_path.open(encoding="utf-8", newline="") as stream:
            return {row["trial_id"] for row in csv.DictReader(stream) if row.get("trial_id")}

    def next_trial(self) -> Trial | None:
        return next(
            (trial for trial in self.trials if trial.trial_id not in self.completed_ids),
            None,
        )

    def start_next(self, time_s: float) -> Trial | None:
        if self.current is not None:
            raise RuntimeError("finish the active trial before starting another")
        self.current = self.next_trial()
        if self.current is not None:
            self.started_at = float(time_s)
        return self.current

    def finish(self, outcome: str, time_s: float) -> dict[str, str]:
        if outcome not in {"pass", "fail"}:
            raise ValueError("outcome must be pass or fail")
        if self.current is None or self.started_at is None:
            raise RuntimeError("no trial is active")
        finished_at = float(time_s)
        if finished_at < self.started_at:
            raise ValueError("finish time cannot precede trial start")

        row = {
            "trial_id": self.current.trial_id,
            "scenario": self.current.scenario,
            "placement": self.current.placement,
            "command": self.current.command,
            "target": self.current.target,
            "outcome": outcome,
            "started_sim_time_s": f"{self.started_at:.3f}",
            "finished_sim_time_s": f"{finished_at:.3f}",
            "duration_s": f"{finished_at - self.started_at:.3f}",
        }
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        needs_header = not self.results_path.exists() or self.results_path.stat().st_size == 0
        with self.results_path.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            if needs_header:
                writer.writeheader()
            writer.writerow(row)

        self.completed_ids.add(self.current.trial_id)
        self.current = None
        self.started_at = None
        return row
