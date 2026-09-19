# Door

Owner: **Agent A**. Implements **D1-D4** from [plan.md](../../plan.md), following [the shared contract](../../contracts/model.md).

**Status: implemented and handed off.** Deterministic gap-based cycle
segmentation + a class-balanced random-forest resistance classifier, evaluated
on a held-out validation block with the official IoU-weighted F1 metric, with a
standalone `predict.py` CLI and CSV exporter.

## Data and Metric

- Local data: `DATASET_ROOT/Door` (`Train.csv`, `Train_Segments_Answer.csv`, `Test.csv`).
- Input: one continuous CSV recording (many door-open/close cycles back to back).
- Official metric: **IoU-weighted F1** (greedy same-label one-to-one IoU matching; see [`metric.py`](metric.py) and the Door Info Kit Section 4).
- Output: `door_predictions.csv` with columns `start_time,end_time,prediction`, one row per detected cycle. Labels are exactly `Normal` or `Abnormal resistance`.

## Approach

### Segmentation (deterministic, no training)

Within a door cycle the controller samples every **20 ms**; between cycles the
door idles for **10-59 seconds**. A new cycle therefore starts wherever the gap
between consecutive rows exceeds **500 ms** (`GAP_THRESHOLD_MS` in
[`loader.py`](loader.py)). This threshold sits two orders of magnitude above the
within-cycle interval and below every observed between-cycle gap, so it
recovers all 110 labelled cycles exactly on `Train.csv` and needs no learned
parameters. Per the info kit's guidance, boundaries are detected from what
actually changes at a cycle edge (a long idle gap) rather than trusting a single
motion flag.

### Classification

Each detected cycle is reduced to **34 features** (see `FEATURE_NAMES` in
[`features.py`](features.py)) covering duration, and the mean/std/min/max/range/
percentiles of motor current, voltage, back-EMF, and door position, plus
derived signals (peak-to-mean current ratio, current-time area, power proxy,
position monotonicity, successive-difference RMS). A class-weight-balanced
`RandomForestClassifier` (400 trees, `random_state=42`) handles the 80/30
Normal/Abnormal imbalance.

## Validation split

The final **30 %** of complete labelled cycles (chronological) form one
contiguous validation block; the first **70 %** train the classifier. The split
is on whole cycles ordered by start time, so no cycle is split across the
boundary and no samples overlap. Concretely: 77 training cycles (58 Normal / 19
Abnormal) and 33 validation cycles (22 Normal / 11 Abnormal); the validation
block begins at `2023-7-5-0-50-34-415`.

## Measured performance

Running the **complete** pipeline (segmentation **and** classification) on the
raw validation window — not on pre-segmented ground-truth cycles — with the
classifier trained only on the 70 % block:

| Metric | Value |
|---|---|
| IoU-weighted F1 | **1.0000** |
| Soft recall | 1.0000 |
| Soft precision | 1.0000 |
| True / predicted / matched cycles | 33 / 33 / 33 |

Reproduce with `python -m ml.door.train` (70 % block) then
`python -m ml.door.evaluate`.

### Why the score is perfect, and its limits

This is a genuine result, not leakage: segmentation is deterministic and never
touches labels, inference never reads labels, and features come only from the
sensor signals. Cross-checks: gap-based segmentation recovers 110/110 cycles;
5-fold stratified CV of the classifier scores 100 % accuracy with zero
variance; and the fault signature is physical — abnormal-resistance cycles draw
substantially more current over the cycle (mean current-time area ≈ 2.30 M vs.
1.69 M mA·ms; mean current ≈ 720 vs. 538 mA), matching the "abnormal
opening/closing resistance raises motor current" mechanism in the info kit.

**Limitations.** The provided dataset is small (110 cycles) and the two classes
are cleanly separated, so the held-out `Test.csv` may be harder than this
validation block suggests. The 500 ms segmentation threshold assumes
between-cycle idle gaps stay well above 500 ms and within-cycle sampling stays
well below it, which holds for both provided files but is an assumption about
the acquisition cadence. The model identifies abnormal *resistance*, not its
physical cause.

## Commands

Run from the repository root using your virtual environment's Python.

```text
# Train the classifier on the 70% block (for evaluation)
python -m ml.door.train

# Evaluate the full pipeline on the held-out validation block
python -m ml.door.evaluate

# Freeze: refit on ALL 110 labelled cycles (this is the shipped artifact)
python -m ml.door.train --full

# Predict on a continuous recording
python -m ml.door.predict --input <recording.csv> --output door_predictions.csv [--artifacts <dir>]

# Tests
python -m pytest ml/door/tests/test_door.py -q
```

`--artifacts` is optional and defaults to this package's `artifacts/` directory,
independent of the working directory. Training/evaluation use
`ml.config.get_dataset_root()`; prediction runs on its explicit `--input` and
never reads labels.

## Public API

```python
from ml.door.inference import predict_door
records = predict_door("Test.csv")            # uses artifacts/ by default
# -> [{"start_time": "...", "end_time": "...", "prediction": "Normal"|"Abnormal resistance"}, ...]
```

Records are plain JSON-serializable dicts. Importing any Door module performs no
model loading, data reading, or training. Missing artifacts or invalid input
raise explicit errors — there are no mock fallbacks.

Recording input accepts both the native non-zero-padded timestamps and
timezone-free ISO timestamps. Newly inferred cycle bounds and backend chart
points use `YYYY-MM-DDTHH:MM:SS.sss` with no inferred timezone, as required by
the shared model contract. Existing native-format CSV records remain accepted
by the serializer; the frontend supports older stored runs too. Timestamp
normalization does not change segmentation, features, labels, or trained weights.

## Artifacts

Stored in `artifacts/` (git-ignored except `.gitkeep`):

| File | Contents |
|---|---|
| `door_classifier.joblib` | `{classifier, feature_names, classes}` — the fitted RF plus the feature-order contract. |
| `manifest.json` | Committed-style provenance: creation time, training cycle count, class distribution, split description, feature names, gap threshold, random seed, and exact dependency versions. |

**Regenerate** the shipped artifact from committed code with:

```text
python -m ml.door.train --full
```

The `.joblib` binary is intentionally not committed (see `.gitignore`); the
manifest records everything needed to reproduce it, and the command above
regenerates it deterministically (`random_state=42`).

## Handoff checklist

- [x] Deterministic segmentation + class-balanced classifier implemented.
- [x] Fixed chronological 70/30 validation split documented and reproducible.
- [x] Official IoU-weighted F1 implemented and pipeline evaluated on the raw validation block (score 1.0000).
- [x] `predict_door` contract implemented; standalone CLI writes the exact `start_time,end_time,prediction` schema.
- [x] Frozen artifact refit on all 110 cycles; fresh-process import + predict verified, Python records match exported CSV.
- [x] Focused tests pass (14/14): non-zero-padded timestamps, segmentation, ordering/valid intervals, no-cycle input, allowed labels, metric, CSV schema.
- [x] Artifact manifest + regeneration command recorded.

Stops at the model gate. No backend/frontend work is part of this assignment.
