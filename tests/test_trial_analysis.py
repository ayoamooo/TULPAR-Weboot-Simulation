import csv
import json
from pathlib import Path
import tempfile
import unittest

from core.trial_analysis import summarise_trials


class TrialAnalysisTests(unittest.TestCase):
    def test_summarises_only_recorded_trial_results_and_channel_events(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            results = root / "results.csv"
            with results.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "trial_id", "scenario", "placement", "command", "target", "outcome",
                    "started_sim_time_s", "finished_sim_time_s", "duration_s",
                ])
                writer.writeheader()
                writer.writerow({
                    "trial_id": "T01", "scenario": "approach_operator", "placement": "floor",
                    "command": "come to me", "target": "operator", "outcome": "pass",
                    "started_sim_time_s": "0", "finished_sim_time_s": "5", "duration_s": "5",
                })
            events = root / "events.jsonl"
            records = [
                {"trial_id": "T01", "command": "voice_output", "outcome": "started", "utterance_type": "trial_prompt", "simulated_time_s": 0.1},
                {"trial_id": "T01", "command": "come_to_me", "outcome": "accepted", "simulated_time_s": 0.9},
                {"trial_id": "T01", "command": "voice_output", "outcome": "started", "utterance_type": "response", "simulated_time_s": 1.0},
                {"trial_id": "T01", "command": "face_display", "outcome": "emotion_started", "simulated_time_s": 1.0},
                {"trial_id": "T01", "command": "movement", "outcome": "started", "simulated_time_s": 1.1, "response_time_s": 0.1},
            ]
            events.write_text("".join(json.dumps(event) + "\n" for event in records), encoding="utf-8")

            summary = summarise_trials(results, events)
            self.assertEqual(summary["recorded_total"], 1)
            self.assertEqual(summary["by_scenario"]["approach_operator"]["pass_rate"], 1.0)
            self.assertEqual(summary["movement_response"]["mean_s"], 0.1)
            self.assertEqual(summary["channel_start_spread"]["mean_s"], 0.1)
            self.assertIsNone(summary["stopping_time"])

    def test_empty_results_are_not_reported_as_zero_percent(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            results = root / "results.csv"
            results.write_text(
                "trial_id,scenario,placement,command,target,outcome,started_sim_time_s,finished_sim_time_s,duration_s\n",
                encoding="utf-8",
            )
            summary = summarise_trials(results, root / "missing.jsonl")
            self.assertEqual(summary["recorded_total"], 0)
            self.assertIsNone(summary["by_scenario"]["approach_operator"]["pass_rate"])
            self.assertIsNone(summary["channel_start_spread"])

    def test_rejected_pointing_counts_as_an_unsuccessful_selection(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            results = root / "results.csv"
            with results.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "trial_id", "scenario", "placement", "command", "target", "outcome",
                    "started_sim_time_s", "finished_sim_time_s", "duration_s",
                ])
                writer.writeheader()
                writer.writerow({
                    "trial_id": "T11", "scenario": "approach_marked_target", "placement": "floor",
                    "command": "go to that marker", "target": "target-A", "outcome": "fail",
                    "started_sim_time_s": "0", "finished_sim_time_s": "2", "duration_s": "2",
                })
            events = root / "events.jsonl"
            events.write_text(json.dumps({
                "trial_id": "T11", "command": "target_selection", "outcome": "rejected",
                "simulated_time_s": 1.0,
            }) + "\n", encoding="utf-8")

            summary = summarise_trials(results, events)
            self.assertEqual(summary["target_selection"]["n"], 1)
            self.assertEqual(summary["target_selection"]["accuracy"], 0.0)


if __name__ == "__main__":
    unittest.main()
