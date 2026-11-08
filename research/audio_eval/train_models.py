"""Train local Speech Commands and RAVDESS pilots and export deployable artifacts.

Archives and exported model files remain local and are deliberately excluded from Git.
The held-out test partitions are never used to fit the exported models.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(ROOT / "_deps"))

from run_baselines import DATA, RAVDESS_LABELS, SPEECH_LABELS, ravdess, speech_commands
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC
import joblib


MODELS = ROOT / "models"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fit_model(features: np.ndarray, labels: np.ndarray):
    model = make_pipeline(
        StandardScaler(),
        LinearSVC(C=1.0, class_weight="balanced", random_state=42, max_iter=5000, dual="auto"),
    )
    model.fit(features, labels)
    return model


def score_test(model, features: np.ndarray, labels: np.ndarray, class_names: list[str]) -> dict:
    prediction = model.predict(features)
    supported_labels = np.unique(labels)
    return {
        "n": int(labels.size),
        "accuracy": float(accuracy_score(labels, prediction)),
        "macro_f1_all_classes": float(
            f1_score(labels, prediction, labels=np.arange(len(class_names)), average="macro", zero_division=0)
        ),
        "uar_present_classes": float(
            recall_score(labels, prediction, labels=supported_labels, average="macro", zero_division=0)
        ),
    }


def main() -> None:
    MODELS.mkdir(parents=True, exist_ok=True)

    speech_X, speech_y, speech_val_X, speech_val_y, speech_meta = speech_commands()
    # Use the published train and validation partitions for the final pilot fit.
    # The official test partition is loaded only by the baseline evaluator and is
    # intentionally not passed into this trainer.
    speech_model = fit_model(
        np.concatenate((speech_X, speech_val_X)),
        np.concatenate((speech_y, speech_val_y)),
    )
    speech_test = (speech_meta.pop("test_X"), speech_meta.pop("test_y"))
    rav_X, rav_y, rav_val_X, rav_val_y, rav_test_X, rav_test_y, rav_meta = ravdess()
    rav_model = fit_model(np.concatenate((rav_X, rav_val_X)), np.concatenate((rav_y, rav_val_y)))
    held_out_test_metrics = {
        "speech_commands": score_test(speech_model, *speech_test, SPEECH_LABELS),
        "ravdess": score_test(rav_model, rav_test_X, rav_test_y, RAVDESS_LABELS),
    }

    artifacts = {
        "speech_commands_v0.02.joblib": speech_model,
        "ravdess_emotion.joblib": rav_model,
    }
    for name, model in artifacts.items():
        joblib.dump(model, MODELS / name, compress=3)

    archives = [
        DATA / "speech_commands_v0.02.tar.gz",
        DATA / "speech_commands_test_set_v0.02.tar.gz",
        DATA / "Audio_Speech_Actors_01-24.zip",
    ]
    manifest = {
        "trained_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "feature_extractor": "core.audio_features.mfcc_summary; 26 float32 values (13 MFCC mean + 13 standard deviation)",
        "estimator": "StandardScaler + class-balanced LinearSVC, C=1.0, random_state=42, max_iter=5000",
        "fit_partitions": {
            "speech_commands": ["official training", "official validation"],
            "ravdess": ["actors 01-16 training", "actors 17-20 validation"],
        },
        "excluded_partitions": {
            "speech_commands": ["official test"],
            "ravdess": ["actors 21-24 test"],
        },
        "labels": {"speech_commands": SPEECH_LABELS, "ravdess": RAVDESS_LABELS},
        "training_examples": {
            "speech_commands": int(len(speech_y) + len(speech_val_y)),
            "ravdess": int(len(rav_y) + len(rav_val_y)),
        },
        "held_out_test_metrics": held_out_test_metrics,
        "source_archives_sha256": {p.name: sha256(p) for p in archives},
        "artifacts_sha256": {name: sha256(MODELS / name) for name in artifacts},
        "limitations": [
            "Speech Commands contains isolated words and is not a natural-language command recognizer.",
            "RAVDESS contains acted vocal emotion; predictions do not establish a speaker's true emotional state.",
            "These artifacts are research pilots and do not control Webots motion or replace Vosk transcription.",
        ],
        "source_split_metadata": {
            "speech_commands": {k: speech_meta.get(k) for k in ("dataset", "labels", "total_examples")},
            "ravdess": {k: rav_meta.get(k) for k in ("dataset", "labels", "actors", "total_examples")},
        },
    }
    output = MODELS / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

