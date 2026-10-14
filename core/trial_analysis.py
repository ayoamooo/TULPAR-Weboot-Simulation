"""Summarise only outcomes and event timings recorded from real simulation runs."""

import csv
import json
from collections import defaultdict
from pathlib import Path
import statistics

from core.trial_protocol import build_plan


def _describe(values: list[float]) -> dict[str, float | int] | None:
    if not values:
        return None
    return {
        "n": len(values),
        "mean_s": round(statistics.mean(values), 3),
        "median_s": round(statistics.median(values), 3),
    }


def summarise_trials(results_path: Path, events_path: Path) -> dict:
    with Path(results_path).open(encoding="utf-8", newline="") as stream:
        results = list(csv.DictReader(stream))

    events_by_trial: dict[str, list[dict]] = defaultdict(list)
    events_file = Path(events_path)
    if events_file.exists():
        with events_file.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("trial_id"):
                    events_by_trial[event["trial_id"]].append(event)

    plan_counts: dict[str, int] = defaultdict(int)
    for trial in build_plan():
        plan_counts[trial.scenario] += 1

    by_scenario = {}
    for scenario, planned in plan_counts.items():
        rows = [row for row in results if row.get("scenario") == scenario]
        passed = sum(row.get("outcome") == "pass" for row in rows)
        failed = sum(row.get("outcome") == "fail" for row in rows)
        by_scenario[scenario] = {
            "planned": planned,
            "recorded": len(rows),
            "pass": passed,
            "fail": failed,
            "pass_rate": round(passed / len(rows), 4) if rows else None,
        }

    movement_times: list[float] = []
    stopping_times: list[float] = []
    greeting_times: list[float] = []
    sync_spreads: list[float] = []
    target_selection_outcomes: list[bool] = []
    for row in results:
        trial_id = row.get("trial_id", "")
        events = events_by_trial.get(trial_id, [])
        scenario = row.get("scenario")
        channels: dict[str, float] = {}
        for event in events:
            command = event.get("command")
            outcome = event.get("outcome")
            if command == "movement" and outcome == "started":
                value = event.get("response_time_s")
                if isinstance(value, (int, float)):
                    movement_times.append(float(value))
                channels.setdefault("movement", float(event["simulated_time_s"]))
            elif command == "stop" and outcome == "confirmed":
                value = event.get("stopping_time_s")
                if isinstance(value, (int, float)):
                    stopping_times.append(float(value))
            elif command == "greeting" and outcome == "gesture_started":
                value = event.get("response_time_s")
                if isinstance(value, (int, float)):
                    greeting_times.append(float(value))
                channels.setdefault("gesture", float(event["simulated_time_s"]))
            elif command == "target_selection" and outcome in {"correct", "incorrect", "rejected"}:
                target_selection_outcomes.append(outcome == "correct")
            elif command == "face_display" and outcome == "emotion_started":
                channels.setdefault("face", float(event["simulated_time_s"]))
            elif command == "voice_output" and outcome == "started":
                if event.get("utterance_type", "response") == "response":
                    channels.setdefault("voice", float(event["simulated_time_s"]))

        expected = {"voice", "face", "movement"} if scenario in {
            "approach_operator", "approach_marked_target"
        } else {"voice", "face", "gesture"} if scenario == "greeting" else set()
        if expected.issubset(channels):
            sync_spreads.append(round(max(channels[key] for key in expected) - min(channels[key] for key in expected), 3))

    return {
        "source": "recorded Webots simulation results",
        "planned_total": len(build_plan()),
        "recorded_total": len(results),
        "by_scenario": by_scenario,
        "movement_response": _describe(movement_times),
        "stopping_time": _describe(stopping_times),
        "greeting_response": _describe(greeting_times),
        "channel_start_spread": _describe(sync_spreads),
        "target_selection": {
            "unit": "pointing attempts",
            "n": len(target_selection_outcomes),
            "correct": sum(target_selection_outcomes),
            "accuracy": round(sum(target_selection_outcomes) / len(target_selection_outcomes), 4)
            if target_selection_outcomes else None,
        },
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result_path = root / "logs" / "technical-trial-results.csv"
    events_path = root / "logs" / "tulpar-events.jsonl"
    if not result_path.exists():
        print("No trial results have been recorded yet.")
    else:
        print(json.dumps(summarise_trials(result_path, events_path), indent=2))
