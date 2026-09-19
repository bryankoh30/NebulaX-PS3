# Rail Corrugation model handoff

Rail-only implementation of the existing [model contract](../../contracts/model.md).
Training loads the repository-local `.env` through `ml.config.get_dataset_root()`;
existing environment settings take precedence. Prediction uses explicit inputs only.

## Environment and R1 protocol

Run from the repository root with Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ml.rail.inspect
.\.venv\Scripts\python.exe -m pytest ml/rail -q
```

`inspect` checks the configured `Rail_Corrugation/Train_Labels.csv`, `Train/`, and
`Test/` paths, but never opens Test recordings. Required labels are 234 Normal,
14 Side I, and 24 Side II, with exactly one label for each of 272 training files.

Real recordings have a header and 10,000 rows at 10,000 Hz. The speed pulse is
named `Rotating speed`, contains 0/1, and is separate from 128 vibration/shock
channels. Channel headers name each car (1-8), axle position (1-8), and signal
kind. The reference order is car, position, vibration then shock; loading uses
names and accepts reordered columns. Odd positions 1/3/5/7 are Side I; even
positions 2/4/6/8 are Side II. Each side has 32 vibration and 32 shock channels.
Missing/extra/duplicate headers, nonfinite samples, nonbinary speed pulses, and
recordings of unexpected length fail explicitly.

Validation sorts filenames lexicographically and uses `StratifiedGroupKFold(5,
shuffle=True, random_state=42)`, grouping identical canonical numeric content.
This is necessary because real training files contain duplicates. `validation_split.json` stores the complete
assignment, labels, byte SHA-256 and canonical numeric SHA-256, plus channel
mapping. Each file is one observation and stays entirely within one fold.
Numeric duplicate recordings remain together in a single fold; conflicting
labels within a duplicate group stop inspection.
No session/run identifiers are supplied, so unseen acquisition relationships
cannot be ruled out; these are file-level estimates, not route-level validation.

Local features live in Git-ignored `ml/rail/cache/`; trained artifacts live in
Git-ignored `ml/rail/artifacts/`. Raw inputs, local `.env`, cached features,
generated predictions and model binaries must not be committed.

## R2-R4 commands and interface

After inspection succeeds, execute these phases in order:

```powershell
.\.venv\Scripts\python.exe -m ml.rail.train --baseline
.\.venv\Scripts\python.exe -m ml.rail.smoke --artifacts ml/rail/artifacts/baseline
.\.venv\Scripts\python.exe -m ml.rail.evaluate
.\.venv\Scripts\python.exe -m pytest ml/rail -q
.\.venv\Scripts\python.exe -m ml.rail.train
.\.venv\Scripts\python.exe -m ml.rail.smoke
```

The development baseline fits Random Forest on folds 1-4 only. Evaluation fits
five independent models per candidate, each withholding its assigned fold. It
compares an always-Normal classifier, class-balanced Random Forest, and
class-balanced Extra Trees (500 trees, seed 42, two workers, square-root feature
subsampling). The final train command selects the candidate with highest pooled
out-of-fold Macro F1 (Random Forest wins ties) and refits on all 272 recordings.
It refuses stale evaluations after data, split, or model-code changes.

Features are per-channel RMS, population standard deviation, peak-to-peak and
Pearson kurtosis. Constant channels have kurtosis zero. For every statistic and
signal kind, Side I and Side II retain their own mean/median/maximum, plus signed
and relative contrasts. Pulse transition rate is transitions divided by the
observed `(N-1)/10000` seconds, not a physical speed estimate. No spectral
features, scaling, imputation, feature selection, or deep learning are used.
All statistics are local to each recording; tree fitting uses training folds
only. The content-addressed cache includes input and implementation hashes.

```python
from ml.rail.inference import predict_rail
from ml.rail.serialize import write_predictions

records = predict_rail(["path/to/recording.csv"], artifact_dir="ml/rail/artifacts")
write_predictions(records, "outputs/rail_predictions.csv")
```

```powershell
.\.venv\Scripts\python.exe -m ml.rail.predict --input <file_or_directory> --output outputs/rail_predictions.csv --artifacts ml/rail/artifacts
```

With the virtual environment activated, the requested CLI is also
`python -m ml.rail.predict --input <file_or_directory> --output <rail_predictions.csv> --artifacts <artifact_directory>`.
`artifact_dir=None` resolves beside the inference module, independent of working
directory. The Python API takes a sequence of files and preserves that order;
the CLI discovers directory CSVs in sorted basename order. Output contains
exactly `file_id,prediction`, preserves filename extensions, and uses only
`Normal`, `Side I`, `Side II`. Invalid inputs, empty batches, duplicate output
IDs and missing/incompatible artifacts raise explicit errors. Modules do not
load data or artifacts at import; prediction never loads labels or trains.

`smoke` copies one real training recording of each class into an ignored
temporary directory, then checks single-file CLI, directory CLI and API in
fresh processes. Those processes have an invalid dataset root and unrelated
working directory. It verifies API/CSV agreement, filename preservation and
absence of training/configuration or other subsystem imports.

## Artifact regeneration and transfer

Run the inspection, evaluation and final training commands above. The local
`artifacts/model.joblib` contains the estimator, feature order/version, classes
and dependency versions. `artifacts/manifest.json` is copied to the versioned
`artifact_manifest.json` for handoff, including checksum, channel mapping,
training count, validation score and generation instructions. Transfer the
model and matching manifest separately, or regenerate from the same source,
dataset and recorded package versions. Only load trusted team-generated joblib
files. The artifact is not a portable format across arbitrary scikit-learn
versions; use the exact versions recorded in the manifest.

The complete frozen split is in `validation_split.json`; `evaluation.json`
contains per-class metrics, confusion matrices, each fold's Macro F1 and error
filenames for all six directed confusions. These are evaluation metadata;
feature caches, model binaries and prediction CSVs stay ignored.

Validation uses only 14 Side I and 24 Side II examples. Folds therefore contain
very few minority examples. The same five folds select and report the
best of two models, so the winning score has selection optimism and is not an
independent test estimate. Unknown acquisition relationships and deployment
shift remain unmeasured. The model classifies corrugation side, not location,
physical cause, severity or remaining life.

For an exact environment replay, install the captured lockfile instead of the
broad shared dependency ranges:

```powershell
.\.venv\Scripts\python.exe -m pip install -r ml/rail/requirements-lock.txt
```

See [phase_report.md](phase_report.md) for completed phase checks, commands,
measured results and limitations.

## Measured validation results

The retained statistical Random Forest achieved pooled out-of-fold Macro F1
**0.686685**, versus **0.538012** for Extra Trees and **0.308300** for always
Normal. No organiser Test recording was opened.

| Class | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| Normal | 0.934694 | 0.978632 | 0.956159 |
| Side I | 0.428571 | 0.214286 | 0.285714 |
| Side II | 0.900000 | 0.750000 | 0.818182 |

Five Normal files were false alarms. Eleven Side I cases were missed as Normal;
five Side II cases were missed as Normal and one was assigned Side I. There
were no Side I -> Side II errors. **Side I recall remains weak.** The complete
confusion matrix, error filenames, fold metrics and phase commands are in
[phase_report.md](phase_report.md) and [evaluation.json](evaluation.json).

After the statistical baseline worked, one fixed five-band spectral extension
was tested on the same grouped folds. It reduced Random Forest Macro F1 to
0.598502 and Extra Trees to 0.479920, so its features and implementation were
removed. [evaluation_spectral.json](evaluation_spectral.json) preserves that
comparison. The winning score therefore includes selection over four learned
candidates; it is not an unbiased post-selection test result.

## Final handoff status

R1-R4 are complete. The selected 500-tree class-balanced Random Forest is
refitted on all 272 labelled recordings and saved locally at
`ml/rail/artifacts/model.joblib` (332,662 bytes). Its matching manifest is
[artifact_manifest.json](artifact_manifest.json). Artifact/source checksums,
13 retained tests, fresh-process single-file and directory inference, API/CSV
agreement, dependency compatibility and the separate four-module import check
passed. No app development was started. Other subsystem model readiness is
outside this Rail handoff.

To verify the final local model again:

```powershell
.\.venv\Scripts\python.exe -m ml.rail.smoke
```
