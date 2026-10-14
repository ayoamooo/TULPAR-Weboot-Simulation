import csv
from pathlib import Path
import tempfile
import unittest

from core.trial_recorder import TrialRecorder


class TrialRecorderTests(unittest.TestCase):
    def test_records_only_observed_results_and_resumes_next_trial(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory) / "results.csv"
            recorder = TrialRecorder(path)
            self.assertEqual(recorder.next_trial().trial_id, "T01")
            first = recorder.start_next(1.25)
            self.assertEqual(first.trial_id, "T01")
            with self.assertRaises(RuntimeError):
                recorder.start_next(2.0)
            row = recorder.finish("pass", 4.0)
            self.assertEqual(row["duration_s"], "2.750")

            resumed = TrialRecorder(path)
            self.assertEqual(resumed.next_trial().trial_id, "T02")
            self.assertEqual(resumed.start_next(10.0).trial_id, "T02")
            with path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["outcome"], "pass")

    def test_rejects_unobserved_or_invalid_outcomes(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            recorder = TrialRecorder(Path(directory) / "results.csv")
            with self.assertRaises(RuntimeError):
                recorder.finish("pass", 2.0)
            recorder.start_next(5.0)
            with self.assertRaises(ValueError):
                recorder.finish("unknown", 6.0)
            with self.assertRaises(ValueError):
                recorder.finish("fail", 4.0)


if __name__ == "__main__":
    unittest.main()
