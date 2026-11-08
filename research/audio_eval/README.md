# Audio dataset pilot evaluation

This folder contains a reproducible classical baseline for the two audio datasets referenced by the TULPAR report. It evaluates isolated keyword classification and acted vocal-emotion labels. It does not measure the complete robot, natural-language command recognition, live microphone performance, expression quality, or Raspberry Pi latency.

## Data and permissions

Download the official archives into `data/` (the folder is excluded from Git):

- Speech Commands v0.02 training/validation archive: <https://storage.googleapis.com/download.tensorflow.org/data/speech_commands_v0.02.tar.gz>
- Speech Commands v0.02 official test archive: <https://storage.googleapis.com/download.tensorflow.org/data/speech_commands_test_set_v0.02.tar.gz>
- RAVDESS audio-only speech archive: <https://zenodo.org/records/1188976>

Do not commit the raw audio. RAVDESS is CC BY-NC-SA 4.0. Keep its attribution and non-commercial/share-alike conditions with any permitted derived material.

## Method

The fixed baseline extracts 13 MFCCs per utterance and concatenates their time-wise means and standard deviations (26 values). It standardises features and fits a class-balanced linear SVM with `C=1.0`, random seed 42. Speech Commands uses the ten TFDS target words plus its silence and unknown labels; training and validation paths follow the official lists, and the official test archive is held out. RAVDESS uses all 1,440 speech-only clips and an actor-exclusive split: actors 01–16 train, 17–20 validate, and 21–24 test. No actor occurs in more than one partition.

Reported metrics are accuracy, macro-F1 across the declared classes, unweighted average recall over classes represented in the split, per-class precision/recall/F1/support, and confusion matrices. The test split is used once for final reporting; it is not used to choose the model.

## Run

Install the packages listed in `requirements.txt` into a Python 3.12 environment, then run:

```powershell
python -m pip install -r research/audio_eval/requirements.txt
python research/audio_eval/run_baselines.py
```

The JSON and CSV outputs in `results/` are retained as the local experiment record. Raw datasets and installed dependencies are ignored by Git. Record Python/library versions and archive hashes with every run.

For an exploratory classifier comparison, run:

```powershell
python research/audio_eval/compare_validation_models.py
```

This second script compares lightweight classifiers on the training and validation partitions only. It does not score the held-out test labels and writes `results/validation_model_comparison.json`. Validation metrics are used to inspect trade-offs, not to claim final test performance.

## Validation-only comparison (21 October 2026)

The initial comparison used the same 26 MFCC summary features. For Speech Commands, LinearSVC achieved 51.2% accuracy, 36.4% macro-F1 and 44.8% UAR; logistic regression achieved 28.8%, 34.0% and 50.3%; HistGradientBoosting achieved 66.9%, 36.9% and 32.8%, respectively. The difference between accuracy and UAR shows that accuracy alone can hide weak class-balanced recognition on this imbalanced dataset. For actor-exclusive RAVDESS validation, RBF SVC achieved 38.8% accuracy, 38.2% macro-F1 and 39.8% UAR, the strongest of the five tested candidates on these validation metrics. No alternative model is selected for deployment on this evidence. The already reported held-out pilot scores remain those of the original LinearSVC baseline.

## Interpretation

Speech Commands evaluates isolated single-word clips, not TULPAR's full spoken phrases or performance in the exhibition room. RAVDESS labels acted North American English emotion. Its held-out-actor scores are not evidence of natural emotion recognition or of how well TULPAR's face and arm communicate emotion. Both evaluations are dataset-level software baselines and remain separate from the 40 planned integrated robot trials.
