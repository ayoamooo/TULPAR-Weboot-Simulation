"""Reproducible MFCC + linear SVM baselines for the two TULPAR audio datasets.

Raw archives are downloaded separately and kept under research/audio_eval/data/.
This is a small offline baseline, not the final TULPAR voice pipeline.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
import random
import sys
import tarfile
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent

import numpy as np
import scipy
import scipy.fft
import scipy.signal
# Keep the small scikit-learn wheel isolated from the user's global Python packages.
sys.path.insert(0, str(ROOT / "_deps"))
import sklearn
import soundfile as sf
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC


DATA = ROOT / "data"
RESULTS = ROOT / "results"
RATE = 16_000
N_FFT = 512
FRAME = 400  # 25 ms
HOP = 160  # 10 ms
MELS = 40
MFCCS = 13
SPEECH_WORDS = ["down", "go", "left", "no", "off", "on", "right", "stop", "up", "yes"]
SPEECH_LABELS = SPEECH_WORDS + ["_silence_", "_unknown_"]
RAVDESS_LABELS = ["neutral", "calm", "happy", "sad", "angry", "fearful", "disgust", "surprised"]
EMOTION_CODES = {f"{i:02d}": label for i, label in enumerate(RAVDESS_LABELS, 1)}


def _mel_bank() -> np.ndarray:
    hz = np.linspace(0, RATE / 2, N_FFT // 2 + 1)
    mel = 2595.0 * np.log10(1.0 + hz / 700.0)
    points = np.linspace(mel[0], mel[-1], MELS + 2)
    bank = np.zeros((MELS, len(hz)), dtype=np.float32)
    for i in range(MELS):
        left, centre, right = points[i : i + 3]
        bank[i] = np.maximum(0, np.minimum((mel - left) / (centre - left), (right - mel) / (right - centre)))
    return bank


MEL_BANK = _mel_bank()


def mfcc_summary(audio_bytes: bytes, *, target_seconds: float | None) -> np.ndarray:
    signal, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
    signal = signal.mean(axis=1)
    if sample_rate != RATE:
        divisor = math.gcd(int(sample_rate), RATE)
        signal = scipy.signal.resample_poly(signal, RATE // divisor, int(sample_rate) // divisor).astype(np.float32)
    if target_seconds is not None:
        length = int(RATE * target_seconds)
        signal = signal[:length]
        if len(signal) < length:
            signal = np.pad(signal, (0, length - len(signal)))
    if len(signal) == 0:
        raise ValueError("empty audio")
    padded = np.pad(signal, (N_FFT // 2, N_FFT // 2))
    frames = np.lib.stride_tricks.sliding_window_view(padded, FRAME)[::HOP]
    window = np.hanning(FRAME).astype(np.float32)
    spectrum = np.fft.rfft(frames * window, n=N_FFT, axis=1)
    power = (spectrum.real**2 + spectrum.imag**2).astype(np.float32)
    mel_energy = np.maximum(power @ MEL_BANK.T, 1e-10)
    coefficients = scipy.fft.dct(np.log(mel_energy), type=2, norm="ortho", axis=1)[:, :MFCCS]
    return np.concatenate([coefficients.mean(axis=0), coefficients.std(axis=0)]).astype(np.float32)


def read_tar_text(archive: tarfile.TarFile, members: list[tarfile.TarInfo], ending: str) -> set[str]:
    member = next(m for m in members if PurePosixPath(m.name).name == ending)
    stream = archive.extractfile(member)
    if stream is None:
        raise RuntimeError(f"Missing {ending} in Speech Commands archive")
    return {line.strip().decode("ascii") for line in stream if line.strip()}


def _path_parts(name: str) -> tuple[str, str]:
    parts = PurePosixPath(name).parts
    return (parts[-2], "/".join(parts[-2:])) if len(parts) >= 2 else ("", name)


def speech_commands() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    main_path = DATA / "speech_commands_v0.02.tar.gz"
    test_path = DATA / "speech_commands_test_set_v0.02.tar.gz"
    if not main_path.is_file() or not test_path.is_file():
        raise FileNotFoundError("Download both official Speech Commands v0.02 archives first")

    features: dict[str, list[np.ndarray]] = {split: [] for split in ("train", "validation", "test")}
    labels: dict[str, list[int]] = {split: [] for split in features}
    counts = {split: Counter() for split in features}
    started = time.perf_counter()

    with tarfile.open(main_path, "r:gz") as archive:
        members = archive.getmembers()
        validation = read_tar_text(archive, members, "validation_list.txt")
        official_train_test = read_tar_text(archive, members, "testing_list.txt")
        for index, member in enumerate(members, 1):
            if not member.isfile() or not member.name.lower().endswith(".wav"):
                continue
            folder, relative = _path_parts(member.name)
            if folder == "_background_noise_":
                split = "validation" if PurePosixPath(relative).name == "running_tap.wav" else "train"
                handle = archive.extractfile(member)
                if handle is None:
                    continue
                raw = handle.read()
                audio, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=True)
                audio = audio.mean(axis=1)
                if sr != RATE:
                    divisor = math.gcd(int(sr), RATE)
                    audio = scipy.signal.resample_poly(audio, RATE // divisor, int(sr) // divisor).astype(np.float32)
                for start in range(0, max(0, len(audio) - RATE), RATE // 2):
                    chunk = audio[start : start + RATE]
                    if len(chunk) < RATE:
                        continue
                    buffer = io.BytesIO()
                    sf.write(buffer, chunk, RATE, format="WAV", subtype="PCM_16")
                    features[split].append(mfcc_summary(buffer.getvalue(), target_seconds=1.0))
                    labels[split].append(SPEECH_LABELS.index("_silence_"))
                    counts[split]["_silence_"] += 1
                continue

            split = "validation" if relative in validation else "train"
            # The TFDS test partition comes from its own dedicated archive.
            if relative in official_train_test:
                continue
            label = folder if folder in SPEECH_WORDS else "_unknown_"
            handle = archive.extractfile(member)
            if handle is None:
                continue
            try:
                vector = mfcc_summary(handle.read(), target_seconds=1.0)
            except (RuntimeError, ValueError, sf.SoundFileRuntimeError):
                continue
            features[split].append(vector)
            labels[split].append(SPEECH_LABELS.index(label))
            counts[split][label] += 1
            if index % 10_000 == 0:
                print(f"Speech Commands: scanned {index:,}/{len(members):,} archive entries", flush=True)

    with tarfile.open(test_path, "r:gz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.lower().endswith(".wav"):
                continue
            folder, _ = _path_parts(member.name)
            label = folder if folder in SPEECH_WORDS else ("_silence_" if "silence" in folder else "_unknown_")
            handle = archive.extractfile(member)
            if handle is None:
                continue
            try:
                vector = mfcc_summary(handle.read(), target_seconds=1.0)
            except (RuntimeError, ValueError, sf.SoundFileRuntimeError):
                continue
            features["test"].append(vector)
            labels["test"].append(SPEECH_LABELS.index(label))
            counts["test"][label] += 1

    result = {k: np.stack(v).astype(np.float32) for k, v in features.items()}
    target = {k: np.asarray(v, dtype=np.int64) for k, v in labels.items()}
    report = {
        "dataset": "Speech Commands v0.02 / TFDS label and split conventions",
        "labels": SPEECH_LABELS,
        "counts": {split: dict(counts[split]) for split in counts},
        "total_examples": {split: len(target[split]) for split in target},
        "feature_extraction_seconds": round(time.perf_counter() - started, 2),
    }
    return result["train"], target["train"], result["validation"], target["validation"], {**report, "test_X": result["test"], "test_y": target["test"]}


def ravdess() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    archive_path = DATA / "Audio_Speech_Actors_01-24.zip"
    if not archive_path.is_file():
        raise FileNotFoundError("Download the official RAVDESS speech-audio archive first")
    split_by_actor = {actor: ("train" if actor <= 16 else "validation" if actor <= 20 else "test") for actor in range(1, 25)}
    features: dict[str, list[np.ndarray]] = {split: [] for split in ("train", "validation", "test")}
    labels: dict[str, list[int]] = {split: [] for split in features}
    actors: dict[str, set[int]] = {split: set() for split in features}
    counts = {split: Counter() for split in features}
    started = time.perf_counter()
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(".wav"):
                continue
            actor_match = PurePosixPath(name).parent.name
            if not actor_match.startswith("Actor_"):
                continue
            actor = int(actor_match.split("_")[-1])
            parts = PurePosixPath(name).stem.split("-")
            if len(parts) != 7 or parts[2] not in EMOTION_CODES:
                continue
            emotion = EMOTION_CODES[parts[2]]
            split = split_by_actor[actor]
            try:
                vector = mfcc_summary(archive.read(name), target_seconds=4.0)
            except (RuntimeError, ValueError, sf.SoundFileRuntimeError):
                continue
            features[split].append(vector)
            labels[split].append(RAVDESS_LABELS.index(emotion))
            actors[split].add(actor)
            counts[split][emotion] += 1
    result = {k: np.stack(v).astype(np.float32) for k, v in features.items()}
    target = {k: np.asarray(v, dtype=np.int64) for k, v in labels.items()}
    report = {
        "dataset": "RAVDESS audio-only speech subset",
        "labels": RAVDESS_LABELS,
        "actors": {split: sorted(actors[split]) for split in actors},
        "counts": {split: dict(counts[split]) for split in counts},
        "total_examples": {split: len(target[split]) for split in target},
        "feature_extraction_seconds": round(time.perf_counter() - started, 2),
    }
    return (result["train"], target["train"], result["validation"], target["validation"], result["test"], target["test"], report)


def evaluate(name: str, train_X: np.ndarray, train_y: np.ndarray, val_X: np.ndarray, val_y: np.ndarray, test_X: np.ndarray, test_y: np.ndarray, class_names: list[str], split_report: dict) -> dict:
    model = make_pipeline(StandardScaler(), LinearSVC(C=1.0, class_weight="balanced", random_state=42, max_iter=5000, dual="auto"))
    fit_started = time.perf_counter()
    model.fit(train_X, train_y)
    fit_seconds = time.perf_counter() - fit_started

    metrics = {}
    confusions = {}
    per_class = {}
    for split, x, y in (("validation", val_X, val_y), ("test", test_X, test_y)):
        predicted = model.predict(x)
        recalls = []
        report = classification_report(y, predicted, labels=np.arange(len(class_names)), target_names=class_names, output_dict=True, zero_division=0)
        for label in class_names:
            per_class.setdefault(split, {})[label] = {
                "precision": report[label]["precision"],
                "recall": report[label]["recall"],
                "f1": report[label]["f1-score"],
                "support": int(report[label]["support"]),
            }
            if report[label]["support"]:
                recalls.append(report[label]["recall"])
        metrics[split] = {
            "accuracy": float(np.mean(predicted == y)),
            "macro_f1_all_classes": float(f1_score(y, predicted, labels=np.arange(len(class_names)), average="macro", zero_division=0)),
            "uar_present_classes": float(np.mean(recalls)) if recalls else 0.0,
            "n": int(len(y)),
        }
        confusions[split] = confusion_matrix(y, predicted, labels=np.arange(len(class_names))).tolist()

    return {
        "dataset": name,
        "method": "13 MFCC coefficients, utterance-level mean and standard deviation (26 features); StandardScaler + LinearSVC(C=1.0, class_weight=balanced); fixed seed 42",
        "fit_seconds_cpu": round(fit_seconds, 2),
        "metrics": metrics,
        "per_class": per_class,
        "confusion_matrices": {"labels": class_names, **confusions},
        "split": split_report,
    }


def save_csv(prefix: str, result: dict) -> None:
    with (RESULTS / f"{prefix}_per_class.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "class", "precision", "recall", "f1", "support"])
        for split, entries in result["per_class"].items():
            for label, values in entries.items():
                writer.writerow([split, label, values["precision"], values["recall"], values["f1"], values["support"]])
    with (RESULTS / f"{prefix}_confusion_matrices.json").open("w", encoding="utf-8") as f:
        json.dump(result["confusion_matrices"], f, indent=2)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    speech_X, speech_y, speech_val_X, speech_val_y, speech_report = speech_commands()
    speech_result = evaluate(
        "Speech Commands v0.02", speech_X, speech_y, speech_val_X, speech_val_y,
        speech_report.pop("test_X"), speech_report.pop("test_y"), SPEECH_LABELS, speech_report,
    )
    save_csv("speech_commands", speech_result)
    print("Speech Commands results:", json.dumps(speech_result["metrics"], indent=2), flush=True)

    rav_train_X, rav_train_y, rav_val_X, rav_val_y, rav_test_X, rav_test_y, rav_report = ravdess()
    rav_result = evaluate(
        "RAVDESS audio-only speech subset", rav_train_X, rav_train_y, rav_val_X, rav_val_y,
        rav_test_X, rav_test_y, RAVDESS_LABELS, rav_report,
    )
    save_csv("ravdess", rav_result)
    print("RAVDESS results:", json.dumps(rav_result["metrics"], indent=2), flush=True)

    archives = [DATA / "speech_commands_v0.02.tar.gz", DATA / "speech_commands_test_set_v0.02.tar.gz", DATA / "Audio_Speech_Actors_01-24.zip"]
    final = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__, "compute": "CPU (installed PyTorch build is CPU-only; this classical baseline does not use GPU)"},
        "archive_sha256": {p.name: sha256(p) for p in archives},
        "speech_commands": speech_result,
        "ravdess": rav_result,
        "limitations": [
            "This is a pilot classical baseline, not the final embedded speech-recognition system.",
            "Speech Commands tests isolated dataset keywords, not TULPAR's full natural-language command phrases or microphone-in-room performance.",
            "RAVDESS scores classify acted vocal-emotion labels for held-out actors; they do not measure natural emotion recognition or TULPAR's facial/arm expression quality.",
            "Neither dataset result is a physical robot trial or evidence of real-time performance on Raspberry Pi.",
        ],
    }
    output = RESULTS / "audio_baseline_results.json"
    output.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {output}", flush=True)


if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)
    main()
