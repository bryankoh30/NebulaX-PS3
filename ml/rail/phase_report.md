# Rail phase report

All source changes are under `ml/rail/`. Root README, plan, contracts, official
PS3 references and other subsystem implementations are unchanged. The local
`.env` was read, not overwritten. No Test recording was opened.

## R1 completed

Files: `data.py`, `inspect.py`, `validation_split.json`, `test_rail.py`,
`requirements-lock.txt`, `README.md`, and this report. Existing shared config,
dependencies and ignore rules needed no edits.

Commands run from the repository root:

```powershell
# Python was absent from PATH; the installed Python 3.12.10 created .venv.
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip freeze
.\.venv\Scripts\python.exe -m compileall -q ml/rail
.\.venv\Scripts\python.exe -m ml.rail.inspect
.\.venv\Scripts\python.exe -m pytest ml/rail -q
```

Validation: all 272 recordings passed strict 10,000-row, 129-column numeric
validation. Speed pulses are binary. Counts: 234 Normal, 14 Side I, 24 Side II.
Channel names establish all 128 vibration/shock mappings. The training CSVs
occupy 4,707,527,671 bytes. `pip check` found no broken requirements; 13 tests
passed in 19.25 seconds.

Duplicate pairs (both Normal): Train107.csv/Train115.csv and
Train165.csv/Train187.csv. Canonical numeric hashing confirmed exactly 270
unique recordings. To avoid leakage, validation uses five stratified **group**
folds with seed 42 and identical recordings grouped together. This implements
the plan's duplicate-group rule while retaining file-level predictions.

| Fold | Normal | Side I | Side II | Total |
| --- | ---: | ---: | ---: | ---: |
| 0 | 47 | 3 | 4 | 54 |
| 1 | 47 | 3 | 5 | 55 |
| 2 | 47 | 3 | 5 | 55 |
| 3 | 46 | 3 | 5 | 54 |
| 4 | 47 | 2 | 5 | 54 |

Limitations: unknown acquisition relationships cannot be grouped without
metadata. Duplicate files retain their original weight in file-level metrics
and the final 272-file fit. Windows required approved runtime access outside
the sandbox; initial package downloads were slow. The local cache and all
artifacts are covered by existing Git ignore rules.

Exact next command at this phase boundary:

```powershell
.\.venv\Scripts\python.exe -m ml.rail.train --baseline
```

## R2 completed

Files: `features.py`, `models.py`, `train.py`, `inference.py`, `predict.py`,
`serialize.py`, `smoke.py`, `test_rail.py`, `README.md`. Supporting provenance
code is in `provenance.py`. Local cache and baseline model are Git-ignored.

Commands:

```powershell
.\.venv\Scripts\python.exe -m ml.rail.train --baseline
.\.venv\Scripts\python.exe -m ml.rail.smoke --artifacts ml/rail/artifacts/baseline
```

Validation: 609 statistical features extracted for every file. Models fit on
218 recordings from folds 1-4; fold 0's 54 files remained held out. Preliminary
fold-0 Macro F1: Random Forest **0.763057**, Extra Trees **0.605442**,
always-Normal **0.310231**. The saved Random Forest baseline passed real
single-file and three-file directory inference, Python/CSV agreement, exact
headers/allowed labels, original filenames and fresh-process checks with an
invalid DATASET_ROOT and unrelated working directory. Inference did not import
training, shared dataset configuration, or any other subsystem implementation.

Memory observation: at 175/272 files, PowerShell reported a Python-process
peak working set of 224,141,312 bytes (213.76 MiB); raw files were processed
sequentially. Only small feature vectors are cached.

Limitations: these initial scores are from one development fold, not the final
five-fold report. No spectral features or fitted preprocessing were introduced.
The baseline artifact is a development artifact, not the final all-data model.

Exact next command at this phase boundary:

```powershell
.\.venv\Scripts\python.exe -m ml.rail.evaluate
```

## R3 completed

Files: `evaluate.py`, `provenance.py`, `evaluation.json`,
`evaluation_statistics.json`, `evaluation_spectral.json`, tests and Rail docs.
The temporary spectral extractor was removed after it failed validation.

Commands run:

```powershell
.\.venv\Scripts\python.exe -m ml.rail.evaluate
# Historical experiment only; this temporary flag was removed with rejected features:
.\.venv\Scripts\python.exe -m ml.rail.evaluate --spectral
# Recheck the retained implementation:
.\.venv\Scripts\python.exe -m ml.rail.evaluate
.\.venv\Scripts\python.exe -m pytest ml/rail -q
```

Primary metric is pooled out-of-fold Macro F1, with all three labels included
and zero precision/F1 when a class is never predicted.

| Approach | Macro F1 | Decision |
| --- | ---: | --- |
| Always Normal | 0.308300 | Comparison baseline |
| Statistical Random Forest | **0.686685** | Selected |
| Statistical Extra Trees | 0.538012 | Rejected |
| Statistics + spectral Random Forest | 0.598502 | Rejected |
| Statistics + spectral Extra Trees | 0.479920 | Rejected |

Selected model metrics:

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| Normal | 0.934694 | 0.978632 | 0.956159 | 234 |
| Side I | 0.428571 | 0.214286 | 0.285714 | 14 |
| Side II | 0.900000 | 0.750000 | 0.818182 | 24 |

Confusion matrix: rows are true class, columns predicted class, both ordered
Normal / Side I / Side II.

```text
             Normal  Side I  Side II
Normal          229       3        2
Side I           11       3        0
Side II           5       1       18
```

Normal false alarms: 3 Side I (Train177.csv, Train226.csv, Train7.csv),
2 Side II (Train126.csv, Train169.csv). Side I -> Side II: zero.
Side II -> Side I: one (Train217.csv). Minority misses: 11/14 Side I files
predicted Normal; 5/24 Side II files predicted Normal, plus the one wrong-side
prediction. All error filenames, metrics and confusion matrices for every
candidate are retained in the JSON evaluation reports.

The selected model's fold Macro F1 values are 0.763057, 0.752778, 0.656357,
0.648746, 0.424444 (mean 0.649076, population SD 0.121867). This variation and
weak Side I recall are important limitations, despite the gain over always
Normal. No preprocessing learns from validation data. Features are computed
within each file and each fitted tree ensemble sees only its training folds.

The bounded spectral experiment used per-channel mean removal, a symmetric
Hann window, a one-sided real FFT, and relative power in fixed bands [0,100),
[100,500), [500,1000), [1000,2500), [2500,5000] Hz. Channel features, side
mean/median/max, and signed/relative contrasts were appended to the statistical
features (1369 total). It used the same seed-42 grouped folds and unchanged
500-tree classifiers. Both scores decreased, so no spectral features remain
in the deployed code. `evaluation_spectral.json` preserves the measurements;
its source hashes refer to the discarded experiment, not the final source.

The final statistical evaluation reproduced the original scores exactly.
Runtime with a warm feature cache was 13.41 seconds, peak process working set
172,544,000 bytes (164.55 MiB). The 272 x 609 feature matrix is 1,325,184 bytes.
The full spectral comparison, including raw extraction, took 126.56 seconds
and peaked at 239,558,656 bytes. Final retained tests: **13 passed in 17.48s**;
the temporary spectral version also passed its 14 checks before rejection.

Limitations: model and feature comparison used the same folds as reported
metrics, so selection optimism remains. With only 14 Side I examples, this is
a limited prototype rather than a reliable Side I fault detector. No Test
recordings informed these decisions, and no independent test score is claimed.

Exact next command at this phase boundary:

```powershell
.\.venv\Scripts\python.exe -m ml.rail.train
```

## R4 completed: Rail handoff gate

Files: final `artifact_manifest.json`, `README.md`, and this report. Final local
model and matching manifest are in Git-ignored `ml/rail/artifacts/`.

Commands:

```powershell
.\.venv\Scripts\python.exe -m ml.rail.train
.\.venv\Scripts\python.exe -m ml.rail.smoke
.\.venv\Scripts\python.exe -c "import ml.door.inference, ml.rail.inference, ml.acv.inference, ml.shm.inference; print('All four inference modules import successfully')"
git diff --check
git status --short
git check-ignore .env ml/rail/cache/probe.npz ml/rail/artifacts/model.joblib outputs/rail_predictions.csv
```

Validation: selected statistical Random Forest refit on **all 272** recordings.
Final artifact: `ml/rail/artifacts/model.joblib`, 332,662 bytes.
SHA-256: `9a614c574715d098b252524a5871e853eda30b265a337f66def62df15d6be002`.
Artifact and every Python source checksum match the versioned manifest.

Fresh-process verification passed for single-file CLI, three-file directory
CLI, and Python API. CSV headers are exactly `file_id,prediction`; labels are
exactly Normal / Side I / Side II; original filenames and extensions are
preserved; API and CSV records agree. Children ran from an unrelated directory
with an invalid DATASET_ROOT. Rail inference loaded no labels, configuration,
training modules, app services, or other subsystem implementations. The
separate four-module shared import check passed. `pip check` passed in R1.

The exact dependency lockfile and artifact manifest are provided. Python was
3.12.10; principal packages were NumPy 2.5.3, pandas 2.3.3, SciPy 1.18.1,
scikit-learn 1.9.1, joblib 1.6.0 and python-dotenv 1.2.3. Regeneration commands
and the reusable API/CSV functions are documented in the Rail README.

Limitations: the model remains weak on Side I and has no organiser Test score.
Artifacts are local only; transfer the model plus its matching manifest
separately or regenerate. Other subsystems were checked for imports only;
their model readiness and the global four-model gate are their owners' work.
No backend/frontend, other subsystem implementation, root README, plan,
contract or official reference was changed. No commit or PR was created.

**Stopped at the Rail model handoff gate.** Exact next command for the receiving
teammate to verify the local handoff:

```powershell
.\.venv\Scripts\python.exe -m ml.rail.smoke
```
