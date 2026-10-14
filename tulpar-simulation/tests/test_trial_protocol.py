import csv
from collections import Counter
from pathlib import Path
import tempfile
import unittest

from core.trial_protocol import build_plan, write_plan


class TrialProtocolTests(unittest.TestCase):
    def test_report_allocation_has_distinct_ids_and_greeting_modes(self):
        trials = build_plan()
        self.assertEqual(len(trials), 40)
        self.assertEqual(len({trial.trial_id for trial in trials}), 40)
        self.assertEqual(trials[0].trial_id, "T01")
        self.assertEqual(trials[-1].trial_id, "T40")
        self.assertEqual(Counter(trial.scenario for trial in trials), {
            "approach_operator": 10,
            "approach_marked_target": 10,
            "stop": 10,
            "greeting": 10,
        })
        greeting = [trial for trial in trials if trial.scenario == "greeting"]
        self.assertEqual(Counter(trial.placement for trial in greeting), {"floor": 5, "tabletop": 5})

    def test_export_contains_only_planned_inputs(self):
        # The workspace is writable even when the OS temp directory is sandboxed.
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory) / "plan.csv"
            write_plan(path)
            with path.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(reader.fieldnames, ["trial_id", "scenario", "placement", "command", "target"])
                self.assertEqual(len(list(reader)), 40)


if __name__ == "__main__":
    unittest.main()
