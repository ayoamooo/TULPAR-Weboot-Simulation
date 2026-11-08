import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "research" / "audio_eval" / "train_models.py"
SPEC = importlib.util.spec_from_file_location("tulpar_train_models", SCRIPT)
TRAINING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRAINING)


class AudioModelTrainingTests(unittest.TestCase):
    def test_trained_pipeline_round_trips_and_predicts_synthetic_features(self):
        features = np.vstack(
            [np.zeros(26), np.full(26, 0.1), np.full(26, 2.0), np.full(26, 2.1)]
        ).astype(np.float32)
        labels = np.array([0, 0, 1, 1])
        model = TRAINING.fit_model(features, labels)

        with tempfile.TemporaryDirectory(dir=SCRIPT.parent) as folder:
            path = Path(folder) / "pilot.joblib"
            TRAINING.joblib.dump(model, path)
            loaded = TRAINING.joblib.load(path)
            self.assertEqual(loaded.predict(features).tolist(), labels.tolist())

    def test_test_metrics_use_all_examples_and_present_class_recall(self):
        class FixedModel:
            def predict(self, features):
                return np.array([0, 1, 1])

        result = TRAINING.score_test(
            FixedModel(), np.zeros((3, 26), dtype=np.float32), np.array([0, 0, 1]), ["a", "b"]
        )
        self.assertEqual(result["n"], 3)
        self.assertAlmostEqual(result["accuracy"], 2 / 3)
        self.assertAlmostEqual(result["uar_present_classes"], 0.75)


if __name__ == "__main__":
    unittest.main()

