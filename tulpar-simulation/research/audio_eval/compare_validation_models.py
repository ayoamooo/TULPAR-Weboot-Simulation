"""Compare lightweight classifiers on validation splits only.

The official test labels are deliberately never scored here. This script
re-extracts the official training/validation features and writes a separate
validation-only comparison artifact.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "_deps"))
sys.path.insert(0, str(ROOT))

from run_baselines import RAVDESS_LABELS, SPEECH_LABELS, ravdess, speech_commands
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC, SVC
from sklearn.linear_model import LogisticRegression


def metrics(model, train_x, train_y, val_x, val_y, class_names):
    started = time.perf_counter()
    model.fit(train_x, train_y)
    fit_seconds = time.perf_counter() - started
    predicted = model.predict(val_x)
    recalls = recall_score(
        val_y,
        predicted,
        labels=np.arange(len(class_names)),
        average=None,
        zero_division=0,
    )
    return {
        "validation_accuracy": float(accuracy_score(val_y, predicted)),
        "validation_macro_f1_all_classes": float(
            f1_score(
                val_y,
                predicted,
                labels=np.arange(len(class_names)),
                average="macro",
                zero_division=0,
            )
        ),
        "validation_uar_present_classes": float(np.mean(recalls)),
        "validation_examples": int(len(val_y)),
        "fit_seconds_cpu": round(fit_seconds, 3),
    }


def main():
    results = {
        "purpose": "Model selection comparison on validation splits only; test split not scored or used for selection.",
        "feature_method": "13 MFCCs represented by utterance mean and standard deviation (26 features).",
        "datasets": {},
    }

    sx, sy, svx, svy, sreport = speech_commands()
    del sreport  # Includes test features by API, but no test labels or scores enter this comparison.
    speech_models = {
        "LinearSVC_balanced_C1": make_pipeline(
            StandardScaler(),
            LinearSVC(C=1.0, class_weight="balanced", random_state=42, max_iter=5000, dual="auto"),
        ),
        "LogisticRegression_balanced_C1": make_pipeline(
            StandardScaler(),
            LogisticRegression(C=1.0, class_weight="balanced", max_iter=400, random_state=42),
        ),
        "HistGradientBoosting_100iter": HistGradientBoostingClassifier(
            max_iter=100, learning_rate=0.1, max_leaf_nodes=31, random_state=42
        ),
    }
    speech_results = {}
    for name, model in speech_models.items():
        print(f"Speech Commands validation: fitting {name}", flush=True)
        speech_results[name] = metrics(model, sx, sy, svx, svy, SPEECH_LABELS)
        print(json.dumps({name: speech_results[name]}), flush=True)
    results["datasets"]["speech_commands_v0.02"] = {
        "train_examples": int(len(sy)),
        "validation_examples": int(len(svy)),
        "labels": SPEECH_LABELS,
        "models": speech_results,
    }

    rx, ry, rvx, rvy, _rtx, _rty, rreport = ravdess()
    rav_models = {
        "LinearSVC_balanced_C1": make_pipeline(
            StandardScaler(),
            LinearSVC(C=1.0, class_weight="balanced", random_state=42, max_iter=5000, dual="auto"),
        ),
        "LogisticRegression_balanced_C1": make_pipeline(
            StandardScaler(),
            LogisticRegression(C=1.0, class_weight="balanced", max_iter=400, random_state=42),
        ),
        "SVC_RBF_C1": make_pipeline(
            StandardScaler(), SVC(C=1.0, kernel="rbf", class_weight="balanced")
        ),
        "ExtraTrees_300": ExtraTreesClassifier(
            n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1, min_samples_leaf=2
        ),
        "HistGradientBoosting_100iter": HistGradientBoostingClassifier(
            max_iter=100, learning_rate=0.1, max_leaf_nodes=31, random_state=42
        ),
    }
    rav_results = {}
    for name, model in rav_models.items():
        print(f"RAVDESS validation: fitting {name}", flush=True)
        rav_results[name] = metrics(model, rx, ry, rvx, rvy, RAVDESS_LABELS)
        print(json.dumps({name: rav_results[name]}), flush=True)
    results["datasets"]["ravdess_speech_only"] = {
        "train_examples": int(len(ry)),
        "validation_examples": int(len(rvy)),
        "actors": rreport["actors"],
        "labels": RAVDESS_LABELS,
        "models": rav_results,
    }

    results["warning"] = (
        "Validation scores are exploratory model-selection evidence, not final test results or TULPAR performance. "
        "Any selected frozen model would require a separately documented final evaluation; the existing pilot test scores remain unchanged."
    )
    output = ROOT / "results" / "validation_model_comparison.json"
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {output}", flush=True)


if __name__ == "__main__":
    main()
