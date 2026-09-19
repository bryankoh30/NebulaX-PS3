# SHM

Owner: **Agent C**. Standalone fatigue-damage regression following [the shared contract](../../contracts/model.md). The backend reuses this package's inference and CSV serializer.

**Status: implemented.** Headerless signal loading, feature extraction, repeated file-level validation, frozen-artifact inference, and shared CSV export are implemented. Artifacts are generated or transferred separately and are not included in a fresh clone.

## Data and Metric

- Local data: `DATASET_ROOT/SHM`.
- Input: one headerless CSV recording or a directory of CSV recordings.
- Official metric: `max(0, 1 - MAPE)` using fractional MAPE (0.10 = 10% error = 0.90 score).
- Output: `shm_predictions.csv`, exact columns `file_id,prediction`, one finite nonnegative numeric estimate per original basename.

## Features and validation

Statistical features include distribution summaries, RMS, ranges and successive differences. The progressive comparison uses 15 statistics or 37 combined statistics/distribution features. Median, standardized Ridge, and Extra Trees candidates are compared on the same `RepeatedKFold(n_splits=5, n_repeats=10, random_state=42)` partitions, with whole files kept together and fitted preprocessing confined to each training fold.

This is a documented implementation variation from the plan's single five-fold/random-forest baseline: it uses repeated folds and Extra Trees. Candidate selection minimizes mean fold MAPE, breaking ties by its standard deviation. The chosen estimator is refit on all labelled training files; inference loads that saved bundle and never reads training labels or trains.

The existing [artifact manifest](artifact_manifest.json) records the statistics-only Extra Trees model: mean CV MAPE **0.2448363870** and averaged-repeat OOF MAPE **0.2400505862**. Their derived scores are **0.7551636130** and **0.7599494138**, respectively. These are arithmetic conversions of the historical manifest, not new measurements. `CV_official_score` applies the formula to mean fold MAPE; `OOF_official_score` applies it to MAPE of each file's predictions averaged across repeats. These are distinct summaries and must not be interchanged.

Evaluation and saved metadata now expose both MAPE values and both corresponding scores. Reusing folds for candidate selection and reporting introduces selection optimism. The small supplied dataset contains healthy operating conditions; the output is a fatigue-damage estimate, not a fault class, failure probability, or remaining useful life.

## Commands

Run from the repository root using your virtual environment's Python:

```text
# Uses DATASET_ROOT from the repository-local .env (or --dataset-root PATH).
python -m ml.shm.train
python -m ml.shm.evaluate
# Explicit input inference, no dataset-root or label dependency.
python -m ml.shm.predict --input <recording.csv_or_directory> --output <output.csv>
python -m pytest ml/shm/tests -q
```

`--artifacts PATH` overrides the package-local `artifacts/` directory. Training writes ignored feature, experiment-comparison and OOF tables under `outputs/`; evaluation prints comparison results without replacing the deployment model. These commands describe the implementation; the integration cleanup did not execute training or dataset inference.

## Handoff

- `artifacts/model.joblib`: model, feature groups and order, model name, target transform, and random seed.
- `artifacts/metadata.json`: selected experiment, MAPE/score summaries, hyperparameters, feature order, creation time.
- `artifact_manifest.json`: versioned description and historical training dependencies. Regeneration uses configured external training data; no in-repository dataset is required.
- `serialize.py`: validates the complete batch before writing; reused by the CLI and backend, preserving numeric precision and excluding review/application metadata.
- Missing model artifacts fail explicitly. Obtain the owner's trusted bundle or run the explicit training command; inference never substitutes a fabricated estimate.
